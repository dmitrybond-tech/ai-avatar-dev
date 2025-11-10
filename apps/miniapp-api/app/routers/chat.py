from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, List, Literal, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from ..rag import answer, embed, index_faiss

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


def _rag_mode() -> Literal["extractive", "llm"]:
    raw = (os.getenv("RAG_MODE") or "extractive").strip().lower()
    if raw not in {"extractive", "llm"}:
        return "extractive"
    return raw  # type: ignore[return-value]


SMART_CHAT_DEFAULT = _env_bool("SMART_CHAT", False)
RAG_TOPK = _env_int("RAG_TOPK", default=3, minimum=1, maximum=10)
RATE_PER_MINUTE = _env_int("SMART_CHAT_RATE_LIMIT", default=6, minimum=0, maximum=60)
DAILY_BUDGET = _env_int("SMART_CHAT_DAILY_BUDGET", default=40, minimum=0, maximum=500)
LLM_DAILY_BUDGET = _env_int("SMART_CHAT_LLM_DAILY_BUDGET", default=10, minimum=0, maximum=200)
DEFAULT_LANG = (os.getenv("DEFAULT_LANG") or "ru").lower()
LLM_MODEL = os.getenv("SMART_CHAT_LLM_MODEL", "gpt-4o-mini")
LLM_PROVIDER = os.getenv("SMART_CHAT_LLM_PROVIDER", "openai").lower()


class _LimiterState(Dict[str, object]):
    minute_window: int
    minute_count: int
    day_key: str
    day_count: int
    llm_count: int


class RateLimiter:
    def __init__(self, per_minute: int, daily_budget: int, llm_daily_budget: int) -> None:
        self.per_minute = per_minute
        self.daily_budget = daily_budget
        self.llm_daily_budget = llm_daily_budget
        self._buckets: Dict[str, _LimiterState] = {}
        self._lock = Lock()

    def consume(self, key: str) -> None:
        with self._lock:
            state = self._get_state(key)
            now = time.time()
            minute_window = int(now // 60)
            day_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            if state["minute_window"] != minute_window:
                state["minute_window"] = minute_window
                state["minute_count"] = 0
            if state["day_key"] != day_key:
                state["day_key"] = day_key
                state["day_count"] = 0
                state["llm_count"] = 0

            if self.per_minute and state["minute_count"] >= self.per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={"error": "rate_limited", "retry_after": 60},
                )
            if self.daily_budget and state["day_count"] >= self.daily_budget:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={"error": "daily_budget_exceeded"},
                )

            state["minute_count"] += 1
            state["day_count"] += 1

    def can_use_llm(self, key: str) -> bool:
        with self._lock:
            state = self._get_state(key)
            day_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            if state["day_key"] != day_key:
                state["day_key"] = day_key
                state["day_count"] = 0
                state["llm_count"] = 0
            if not self.llm_daily_budget:
                return True
            return state["llm_count"] < self.llm_daily_budget

    def commit_llm(self, key: str) -> None:
        with self._lock:
            state = self._get_state(key)
            day_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            if state["day_key"] != day_key:
                state["day_key"] = day_key
                state["day_count"] = 0
                state["llm_count"] = 0
            state["llm_count"] += 1

    def _get_state(self, key: str) -> _LimiterState:
        if key not in self._buckets:
            self._buckets[key] = _LimiterState(
                minute_window=0,
                minute_count=0,
                day_key="",
                day_count=0,
                llm_count=0,
            )
        return self._buckets[key]


limiter = RateLimiter(RATE_PER_MINUTE, DAILY_BUDGET, LLM_DAILY_BUDGET)


class ChatConfig(BaseModel):
    smart_default: bool
    rag_mode: Literal["extractive", "llm"]
    topk: int


class ChatSource(BaseModel):
    id: str
    title: str
    score: float


class ChatAskIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    lang: Optional[Literal["ru", "en"]] = None
    llm: Optional[bool] = False


class ChatAskOut(BaseModel):
    reply: str
    sources: List[ChatSource]
    mode: Literal["extractive", "llm"]


@router.get("/config", response_model=ChatConfig, response_model_by_alias=False)
async def get_chat_config() -> ChatConfig:
    return ChatConfig(
        smart_default=SMART_CHAT_DEFAULT and _rag_mode() == "llm",
        rag_mode=_rag_mode(),
        topk=RAG_TOPK,
    )


@router.post("/ask", response_model=ChatAskOut)
async def ask(request: Request, payload: ChatAskIn) -> ChatAskOut:
    rate_key = _rate_key(request)
    limiter.consume(rate_key)

    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"error": "empty_text"})

    lang = _resolve_lang(request, payload.lang)

    try:
        embedding = embed.embed_texts([text])
    except Exception as exc:  # pragma: no cover - safety net
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"error": "embedding_failed"}) from exc

    try:
        hits = index_faiss.search(embedding[0], top_k=RAG_TOPK, preferred_lang=lang)
    except Exception as exc:  # pragma: no cover - safety net
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"error": "retrieval_failed"}) from exc
    reply_text, sources = answer.build_extractive_answer(text, hits, lang)
    mode: Literal["extractive", "llm"] = "extractive"

    should_llm = bool(payload.llm) and _rag_mode() == "llm"
    if should_llm and limiter.can_use_llm(rate_key):
        refined = await _maybe_llm_reply(text, reply_text, hits, lang)
        if refined:
            limiter.commit_llm(rate_key)
            reply_text = refined
            mode = "llm"

    return ChatAskOut(
        reply=reply_text,
        sources=[ChatSource(**source) for source in sources],
        mode=mode,
    )


class ChatStubPayload(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


@router.post("/stub", response_model=ChatAskOut, include_in_schema=False)
async def ask_stub(request: Request, payload: ChatStubPayload) -> ChatAskOut:
    """Backward-compatible stub endpoint for legacy clients."""
    proxy = ChatAskIn(text=payload.message)
    return await ask(request, proxy)


def _rate_key(request: Request) -> str:
    headers = request.headers
    candidate = (
        headers.get("X-User-Id")
        or headers.get("X-USER-ID")
        or headers.get("X-Telegram-User-Id")
        or headers.get("X-User")
    )
    if candidate:
        return candidate.strip() or "anon"
    return "anon"


def _resolve_lang(request: Request, preferred: Optional[str]) -> Literal["ru", "en"]:
    if preferred in {"ru", "en"}:
        return preferred  # type: ignore[return-value]
    header = request.headers.get("X-Locale") or request.headers.get("Accept-Language") or ""
    header = header.lower()
    if header.startswith("en"):
        return "en"  # type: ignore[return-value]
    if header.startswith("ru"):
        return "ru"  # type: ignore[return-value]
    if DEFAULT_LANG.startswith("en"):
        return "en"  # type: ignore[return-value]
    return "ru"  # type: ignore[return-value]


async def _maybe_llm_reply(
    user_query: str,
    draft: str,
    hits: List[index_faiss.SearchHit],
    lang: Literal["ru", "en"],
) -> Optional[str]:
    if _rag_mode() != "llm":
        return None

    context_lines = []
    for hit in hits:
        if not context_lines:
            context_lines.append(f"{hit.record.title}: {', '.join(hit.record.tags[:4])}")
        snippet_examples = hit.record.examples[:2] or hit.record.bullets[:2]
        if snippet_examples:
            joined = "; ".join(snippet_examples)
            context_lines.append(f"Examples: {joined}")

    system_prompt = (
        "You are an assistant that polishes answers assembled from a skills knowledge base. "
        "Stay concise, neutral, and grounded in the provided context. "
        "Do not invent new capabilities."
    )
    if lang == "ru":
        system_prompt += " Ответ давай на русском языке."
    else:
        system_prompt += " Answer in English."

    user_prompt = (
        f"User question:\n{user_query}\n\n"
        f"Draft answer:\n{draft}\n\n"
        f"Context:\n" + "\n".join(context_lines)
    )

    if LLM_PROVIDER == "groq":
        try:
            from ..llm.providers.groq import GroqConfigError, generate_groq
        except ImportError:
            return None
        try:
            reply, _usage = await generate_groq(user_prompt, system_prompt, temperature=0.2)
        except GroqConfigError:
            return None
        except Exception:
            return None
        return reply

    if LLM_PROVIDER != "openai":
        return None
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    payload = {
        "model": LLM_MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
    except Exception:
        return None

    try:
        message = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None

    if isinstance(message, str) and message.strip():
        return message.strip()
    return None


