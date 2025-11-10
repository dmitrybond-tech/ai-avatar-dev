from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import select

from ..models.chat import ChatMessage, ChatSession, get_session
from ..services.llm import llm_reply
from ..utils.telegram import send_message, verify_webapp_initdata

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

SMART_CHAT_ON = os.getenv("SMART_CHAT", "off").strip().lower() in {"1", "true", "yes", "on"}
_rag = (os.getenv("RAG_MODE") or "extractive").strip().lower()
RAG_MODE: Literal["extractive", "llm"] = "llm" if _rag == "llm" else "extractive"
CHAT_PERSONA = (os.getenv("CHAT_PERSONA") or "dima").strip().lower()
LLM_PROVIDER = (os.getenv("LLM_PROVIDER") or "openai").strip().lower()
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()
SKILLS_URL_BASE = "http://127.0.0.1:8000/api/skills"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or ""


class ConfigResponse(BaseModel):
    persona: str
    smart_chat: bool
    rag_mode: Literal["extractive", "llm"]
    provider: str
    model: str


class AskRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    lang: str = Field(default="ru")
    llm: bool = Field(default=False)
    session_id: Optional[str] = Field(default=None)
    tg_init_data: Optional[str] = Field(default=None)


class AskResponse(BaseModel):
    reply: str
    mode: Literal["llm", "stub"]
    session_id: str
    persona: str


class ExportRequest(BaseModel):
    session_id: str = Field(..., min_length=8)
    tg_init_data: Optional[str] = Field(default=None)


class ExportResponse(BaseModel):
    ok: bool
    count: int
    bytes: int
    already_exported: bool = Field(default=False)


def _persona_intro(lang: str, persona: str) -> str:
    if lang == "en":
        return "Hi! I'm Dima's assistant. How can I help you today?"
    return "Привет! Я ассистент Димы. Чем могу помочь?"


def _normalize_lang(lang: str) -> Literal["ru", "en"]:
    lang = (lang or "").strip().lower()
    if lang.startswith("en"):
        return "en"
    return "ru"


def _has_llm_credentials(provider: str) -> bool:
    if provider == "groq":
        return bool(os.getenv("GROQ_API_KEY"))
    if provider == "openai":
        return bool(os.getenv("OPENAI_API_KEY"))
    return False


async def _fetch_skills_snip(lang: str) -> str:
    url = f"{SKILLS_URL_BASE}?lang={lang}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:  # noqa: BLE001 - external call
        logger.debug("Skills fetch failed: %s", exc)
        return ""

    if not isinstance(payload, list):
        return ""

    lines: list[str] = []
    for item in payload[:5]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or item.get("slug") or "").strip()
        summary = str(item.get("short") or "").strip()
        if not title:
            continue
        if summary:
            lines.append(f"- {title}: {summary}")
        else:
            lines.append(f"- {title}")
    return "\n".join(lines)


def _stub_reply(lang: str, skills_snip: str) -> str:
    if lang == "en":
        parts = [
            "Here is what Dima focuses on right now:",
        ]
        if skills_snip:
            parts.append(skills_snip)
        parts.append("If you need a deeper answer, I can forward this to Dima.")
        return "\n".join(parts)
    parts = ["Коротко о текущих направлениях Димы:"]
    if skills_snip:
        parts.append(skills_snip)
    parts.append("Если понадобится подробнее, я передам запрос Диме.")
    return "\n".join(parts)


def _format_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


async def _send_transcript(token: str, chat_id: int, text: str) -> bool:
    if not text:
        return False

    max_len = 4000
    chunks: list[str] = []
    cursor = 0
    while cursor < len(text):
        chunk = text[cursor : cursor + max_len]
        chunks.append(chunk)
        cursor += max_len

    ok = True
    for idx, chunk in enumerate(chunks):
        prefix = ""
        if len(chunks) > 1:
            prefix = f"[{idx + 1}/{len(chunks)}]\n"
        success = await send_message(token, chat_id, f"{prefix}{chunk}")
        if not success:
            ok = False
            break
    return ok


@router.get("/chat/config", response_model=ConfigResponse)
async def chat_config() -> ConfigResponse:
    return ConfigResponse(
        persona=CHAT_PERSONA,
        smart_chat=SMART_CHAT_ON,
        rag_mode=RAG_MODE,  # type: ignore[arg-type]
        provider=LLM_PROVIDER,
        model=LLM_MODEL,
    )


@router.post("/chat/ask", response_model=AskResponse)
async def ask(payload: AskRequest) -> AskResponse:
    lang = _normalize_lang(payload.lang)
    session_id = payload.session_id.strip() if payload.session_id else str(uuid.uuid4())
    raw_text = payload.text.strip()
    if not raw_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "empty_text"})

    tg_user_id: Optional[int] = None
    if payload.tg_init_data and TELEGRAM_TOKEN:
        tg_user_id = verify_webapp_initdata(payload.tg_init_data, TELEGRAM_TOKEN)

    with get_session() as session:
        record = session.get(ChatSession, session_id)
        if record is None:
            record = ChatSession(id=session_id, tg_user_id=tg_user_id, lang=lang)
            session.add(record)
        else:
            if tg_user_id and record.tg_user_id != tg_user_id:
                record.tg_user_id = tg_user_id
            if record.lang != lang:
                record.lang = lang

        message = ChatMessage(session_id=session_id, role="user", text=raw_text)
        session.add(message)
        session.commit()

    skills_snip = await _fetch_skills_snip(lang)
    mode: Literal["llm", "stub"] = "stub"
    reply_body = ""

    provider_ready = _has_llm_credentials(LLM_PROVIDER)
    wants_llm = bool(payload.llm) or (SMART_CHAT_ON and provider_ready)
    if wants_llm and provider_ready:
        reply_text = await asyncio.to_thread(llm_reply, lang, raw_text, skills_snip)
        if reply_text:
            mode = "llm"
            reply_body = reply_text.strip()

    if not reply_body:
        reply_body = _stub_reply(lang, skills_snip)

    reply_text_full = f"{_persona_intro(lang, CHAT_PERSONA)}\n\n{reply_body}".strip()

    with get_session() as session:
        assistant_msg = ChatMessage(session_id=session_id, role="assistant", text=reply_text_full)
        session.add(assistant_msg)
        session.commit()

    return AskResponse(
        reply=reply_text_full,
        mode=mode,
        session_id=session_id,
        persona=CHAT_PERSONA,
    )


@router.post("/chat/export", response_model=ExportResponse)
async def export_chat(payload: ExportRequest) -> ExportResponse:
    session_id = payload.session_id.strip()
    if not session_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "missing_session"})

    if not TELEGRAM_TOKEN:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"error": "telegram_unconfigured"})

    tg_user_id: Optional[int] = None
    with get_session() as session:
        chat_session = session.get(ChatSession, session_id)
        if chat_session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "session_not_found"})

        tg_user_id = chat_session.tg_user_id
        if payload.tg_init_data:
            validated = verify_webapp_initdata(payload.tg_init_data, TELEGRAM_TOKEN)
            if validated:
                tg_user_id = validated
                if chat_session.tg_user_id != validated:
                    chat_session.tg_user_id = validated

        if not tg_user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "missing_user"})

        session.add(chat_session)
        session.commit()

        messages = session.exec(
            select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.ts)
        ).all()

    header_lines = [
        f"Chat session: {session_id}",
        f"Started: {_format_timestamp(chat_session.started_at)}",
        f"Export attempt: {_format_timestamp(datetime.now(timezone.utc))}",
        "",
    ]
    transcript_lines = header_lines.copy()
    for msg in messages:
        transcript_lines.append(f"[{msg.role.upper()}] {_format_timestamp(msg.ts)}")
        transcript_lines.append(msg.text)
        transcript_lines.append("")

    transcript = "\n".join(transcript_lines).strip()
    already_exported = chat_session.exported_at is not None

    ok = True
    if not already_exported:
        ok = await _send_transcript(TELEGRAM_TOKEN, tg_user_id, transcript)
        if ok:
            with get_session() as session:
                fresh = session.get(ChatSession, session_id)
                if fresh:
                    fresh.exported_at = datetime.now(timezone.utc)
                    session.add(fresh)
                    session.commit()
    bytes_len = len(transcript.encode("utf-8"))
    return ExportResponse(
        ok=ok,
        count=len(messages),
        bytes=bytes_len,
        already_exported=already_exported,
    )

