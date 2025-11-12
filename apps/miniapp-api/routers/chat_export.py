"""Chat export and FatContext Grok endpoints."""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..services.chat_store import get_chat_store
from ..services.fatcontext import build_fat_context, format_fat_context_for_grok
from ..services.llm_grok import get_grok_client
from ..services.skills import SkillsRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat-export"])

# Rate limiter for ask_grok (per session)
class _SessionLimiterState(Dict[str, object]):
    last_reset: float
    count: int


class SessionRateLimiter:
    """Simple rate limiter: 5 requests per 30 seconds per session."""
    
    def __init__(self, max_requests: int = 5, window_seconds: int = 30) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._sessions: Dict[str, _SessionLimiterState] = {}
        self._lock = Lock()
    
    def check(self, session_id: str) -> None:
        """Check if session can make a request; raise 429 if rate limited."""
        with self._lock:
            now = time.time()
            state = self._sessions.get(session_id)
            
            if state is None or (now - state["last_reset"]) >= self.window_seconds:
                self._sessions[session_id] = _SessionLimiterState(
                    last_reset=now,
                    count=0,
                )
            
            state = self._sessions[session_id]
            if state["count"] >= self.max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={"error": "rate_limited", "retry_after": self.window_seconds},
                )
            
            state["count"] += 1


_grok_limiter = SessionRateLimiter(max_requests=5, window_seconds=30)


def _resolve_lang(request: Request, preferred: Optional[str]) -> str:
    """Resolve language from request or preferred value."""
    if preferred in {"ru", "en"}:
        return preferred
    header = request.headers.get("X-Locale") or request.headers.get("Accept-Language") or ""
    header = header.lower()
    if header.startswith("en"):
        return "en"
    if header.startswith("ru"):
        return "ru"
    default_lang = (os.getenv("DEFAULT_LANG") or "en").lower()
    return "en" if default_lang.startswith("en") else "ru"


# Request/Response models
class ChatEventRequest(BaseModel):
    session_id: Optional[str] = None
    role: str = Field(..., description="user|assistant|system|bot|grok")
    content: str = Field(..., min_length=1)
    lang: Optional[str] = Field(None, description="ru|en")
    meta: Optional[Dict[str, Any]] = None


class ChatEventResponse(BaseModel):
    session_id: str
    ts: str


class ChatMessagesResponse(BaseModel):
    messages: List[Dict[str, Any]]
    session_id: str
    count: int


class AskGrokRequest(BaseModel):
    session_id: str = Field(..., description="Chat session ID")
    q: str = Field(..., min_length=1, description="User question")
    lang: Optional[str] = Field(None, description="ru|en")
    selected: Optional[List[str]] = Field(None, description="Optional skill slugs to include")


class AskGrokResponse(BaseModel):
    answer: str
    used_skills: List[str]
    model: str
    tokens_estimate: int
    from_fatcontext: bool = True


@router.post("/event", response_model=ChatEventResponse)
async def append_event(request: Request, payload: ChatEventRequest) -> ChatEventResponse:
    """Append a chat event to the store."""
    lang = _resolve_lang(request, payload.lang)
    
    chat_store = get_chat_store()
    session_id, ts = chat_store.append_event(
        session_id=payload.session_id,
        role=payload.role,
        content=payload.content,
        lang=lang,
        meta=payload.meta,
    )
    
    return ChatEventResponse(session_id=session_id, ts=ts)


@router.get("/{session_id}", response_model=ChatMessagesResponse)
async def get_chat_messages(
    session_id: str,
    request: Request,
    limit: int = Query(default=50, ge=1, le=100, description="Max number of messages"),
) -> ChatMessagesResponse:
    """Get last N messages from a chat session."""
    chat_store = get_chat_store()
    events = chat_store.read_tail(session_id, limit=limit)
    
    return ChatMessagesResponse(
        messages=events,
        session_id=session_id,
        count=len(events),
    )


@router.get("/{session_id}/export.jsonl")
async def export_jsonl(session_id: str) -> StreamingResponse:
    """Export chat session as JSONL."""
    chat_store = get_chat_store()
    
    def generate() -> Any:
        for line in chat_store.stream_jsonl(session_id):
            yield line
    
    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={
            "Content-Disposition": f'attachment; filename="chat-{session_id}.jsonl"',
        },
    )


@router.get("/{session_id}/export.csv")
async def export_csv(session_id: str) -> StreamingResponse:
    """Export chat session as CSV."""
    chat_store = get_chat_store()
    
    def generate() -> Any:
        for line in chat_store.export_csv(session_id):
            yield line
    
    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="chat-{session_id}.csv"',
        },
    )


@router.get("/{session_id}/export.txt")
async def export_txt(session_id: str) -> StreamingResponse:
    """Export chat session as plain text transcript."""
    chat_store = get_chat_store()
    
    def generate() -> Any:
        for line in chat_store.export_txt(session_id):
            yield line
    
    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="chat-{session_id}.txt"',
        },
    )


@router.post("/ask_grok", response_model=AskGrokResponse)
async def ask_grok(request: Request, payload: AskGrokRequest) -> AskGrokResponse:
    """Ask Grok with FatContext (chat history + skills)."""
    # Check Grok availability
    grok_client = get_grok_client()
    if not grok_client.available:
        api_key_set = bool(os.getenv("XAI_API_KEY"))
        if not api_key_set:
            raise HTTPException(status_code=401, detail="XAI_API_KEY not configured")
        raise HTTPException(status_code=502, detail="Grok provider unavailable")
    
    # Rate limit check
    try:
        _grok_limiter.check(payload.session_id)
    except HTTPException:
        raise
    
    # Resolve language
    lang = _resolve_lang(request, payload.lang)
    
    # Get skills repository
    skills_repo = getattr(request.app.state, "skills_repo", None)
    if skills_repo is None:
        skills_repo = SkillsRepository()
    
    # Check if session exists (at least one event)
    chat_store = get_chat_store()
    existing_events = chat_store.read_tail(payload.session_id, limit=1)
    if not existing_events:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Build FatContext
    try:
        context = build_fat_context(
            session_id=payload.session_id,
            q=payload.q,
            lang=lang,
            selected_skills=payload.selected,
            skills_repo=skills_repo,
        )
    except Exception as exc:
        logger.error("Failed to build FatContext: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to build context") from exc
    
    # Format context for Grok
    context_prompt = format_fat_context_for_grok(context)
    
    # Build system prompt
    system_prompt = (
        "Answer strictly using the provided chat context and skills. "
        "If information is missing, state limits explicitly. "
        "Be concise and helpful."
    )
    if lang == "ru":
        system_prompt += " Отвечай на русском языке."
    else:
        system_prompt += " Answer in English."
    
    # Build user message with context
    user_message = f"{context_prompt}\n\nUser question: {payload.q}"
    
    # Call Grok
    try:
        messages = [{"role": "user", "content": user_message}]
        answer_text = grok_client.ask_grok(system_prompt, messages)
        if not answer_text:
            raise HTTPException(status_code=502, detail="Grok returned empty response")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Grok API call failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail="Grok provider error; try again later") from exc
    
    # Extract used skills from context
    used_skills = [skill.get("slug", "") for skill in context.get("skills_excerpt", [])]
    used_skills = [s for s in used_skills if s]
    
    # Estimate tokens (rough: ~4 chars per token)
    tokens_estimate = (len(payload.q) + len(context_prompt) + len(answer_text)) // 4
    
    # Append user question and Grok answer to transcript
    try:
        # Append user question
        chat_store.append_event(
            session_id=payload.session_id,
            role="user",
            content=payload.q,
            lang=lang,
            meta={"channel": "web"},
        )
        
        # Append Grok answer
        chat_store.append_event(
            session_id=payload.session_id,
            role="grok",
            content=answer_text,
            lang=lang,
            meta={
                "used_skills": used_skills,
                "llm": {
                    "provider": "grok",
                    "model": grok_client._model,
                    "tokens_in": len(payload.q) + len(context_prompt),
                    "tokens_out": len(answer_text),
                },
                "smart_llm": True,
                "channel": "web",
            },
        )
    except Exception as exc:
        logger.warning("Failed to append events to transcript: %s", exc)
        # Don't fail the request if append fails
    
    return AskGrokResponse(
        answer=answer_text,
        used_skills=used_skills,
        model=grok_client._model,
        tokens_estimate=tokens_estimate,
        from_fatcontext=True,
    )

