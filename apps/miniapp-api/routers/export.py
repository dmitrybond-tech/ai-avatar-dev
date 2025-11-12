"""Chat export to Telegram endpoint."""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from ..services.chat_store import get_chat_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/export", tags=["export"])

# Redaction patterns (basic)
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PHONE_PATTERN = re.compile(r'\b\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b')
TOKEN_PATTERN = re.compile(r'\b(bearer|token|api[_-]?key|secret)[\s:=]+[\w-]{20,}\b', re.IGNORECASE)
ID_PATTERN = re.compile(r'\b(id|uuid|session)[\s:=]+[\w-]{20,}\b', re.IGNORECASE)


def _redact_text(text: str, enabled: bool = True) -> str:
    """Basic redaction of sensitive patterns."""
    if not enabled:
        return text
    result = text
    result = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", result)
    result = PHONE_PATTERN.sub("[PHONE_REDACTED]", result)
    result = TOKEN_PATTERN.sub("[TOKEN_REDACTED]", result)
    result = ID_PATTERN.sub("[ID_REDACTED]", result)
    return result


def _redact_dict(obj: Any, enabled: bool = True) -> Any:
    """Recursively redact sensitive data from dict/list structures."""
    if not enabled:
        return obj
    if isinstance(obj, dict):
        return {k: _redact_dict(v, enabled) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact_dict(item, enabled) for item in obj]
    if isinstance(obj, str):
        return _redact_text(obj, enabled)
    return obj


def resolve_tg_env() -> tuple[str, str]:
    """Resolve Telegram token and chat ID from environment variables."""
    token = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID") or os.getenv("ADMIN_CHAT_ID")
    if not token or not chat_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="telegram_env_missing",
        )
    return token, chat_id


class ExportTelegramRequest(BaseModel):
    """Request model for Telegram export."""
    session_id: str = Field(..., description="Chat session ID")
    persona: str = Field(default="dima", description="Persona name")
    messages: List[Dict[str, Any]] = Field(..., description="List of messages")
    meta: Optional[Dict[str, Any]] = Field(default=None, description="Metadata")


class ExportTelegramResponse(BaseModel):
    """Response model for Telegram export."""
    ok: bool
    method: str = Field(..., description="sendDocument or sendMessage")
    bytes: int = Field(..., description="Size of exported data in bytes")


class ClearChatRequest(BaseModel):
    """Request model for clearing chat."""
    session_id: str = Field(..., description="Chat session ID to clear")


class ClearChatResponse(BaseModel):
    """Response model for clearing chat."""
    ok: bool


@router.post("/telegram", response_model=ExportTelegramResponse)
async def export_to_telegram(request: Request, payload: ExportTelegramRequest) -> ExportTelegramResponse:
    """
    Export chat messages to Telegram as JSON document.
    
    Tries sendDocument first, falls back to sendMessage if document fails.
    """
    # Resolve Telegram credentials
    try:
        token, chat_id = resolve_tg_env()
    except HTTPException:
        raise
    
    # Validate and sanitize messages
    allowed_roles = {"user", "assistant", "system"}
    sanitized_messages: List[Dict[str, Any]] = []
    for msg in payload.messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role", "").lower()
        if role not in allowed_roles:
            continue
        content = str(msg.get("content", "")).strip()
        if not content:
            continue
        # Cap content length
        if len(content) > 4000:
            content = content[:4000] + "...[truncated]"
        sanitized_messages.append({
            "role": role,
            "content": content,
            "ts": msg.get("ts", datetime.now(timezone.utc).isoformat()),
        })
    
    if not sanitized_messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="no_valid_messages",
        )
    
    # Build export JSON
    export_data: Dict[str, Any] = {
        "session_id": payload.session_id,
        "persona": payload.persona,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "message_count": len(sanitized_messages),
        "messages": sanitized_messages,
    }
    
    if payload.meta:
        export_data["meta"] = payload.meta
    
    # Apply redaction if enabled
    redact_enabled = os.getenv("REDACT_EXPORT", "true").strip().lower() in {"1", "true", "yes"}
    if redact_enabled:
        export_data = _redact_dict(export_data, enabled=True)
    
    # Serialize to JSON
    json_bytes = json.dumps(export_data, ensure_ascii=False, indent=2).encode("utf-8")
    json_size = len(json_bytes)
    
    # Try sendDocument first
    import httpx
    
    filename = f"chat-export-{payload.session_id}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.json"
    caption = f"Chat export: {payload.persona} ({len(sanitized_messages)} messages)"
    if len(caption) > 1024:
        caption = caption[:1020] + "..."
    
    tg_url = f"https://api.telegram.org/bot{token}/sendDocument"
    
    try:
        # Try sendDocument
        async with httpx.AsyncClient(timeout=15.0) as client:
            files = {
                "document": (filename, json_bytes, "application/json; charset=utf-8"),
            }
            data = {
                "chat_id": chat_id,
                "caption": caption,
            }
            response = await client.post(tg_url, data=data, files=files)
            response.raise_for_status()
            result = response.json()
            if result.get("ok"):
                logger.info("Exported chat to Telegram via sendDocument: session=%s, size=%d", payload.session_id, json_size)
                return ExportTelegramResponse(ok=True, method="sendDocument", bytes=json_size)
    except Exception as exc:
        logger.warning("sendDocument failed, falling back to sendMessage: %s", exc)
        # Fallback to sendMessage
        try:
            # Truncate JSON if too long
            json_text = json_bytes.decode("utf-8")
            max_chars = 3500  # Leave room for markdown formatting
            if len(json_text) > max_chars:
                json_text = json_text[:max_chars] + "\n...[truncated]"
            
            message_text = f"```json\n{json_text}\n```"
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                payload_data = {
                    "chat_id": chat_id,
                    "text": message_text,
                    "parse_mode": "Markdown",
                }
                response = await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json=payload_data,
                )
                response.raise_for_status()
                result = response.json()
                if result.get("ok"):
                    logger.info("Exported chat to Telegram via sendMessage: session=%s, size=%d", payload.session_id, json_size)
                    return ExportTelegramResponse(ok=True, method="sendMessage", bytes=json_size)
        except Exception as send_msg_exc:
            logger.error("Both sendDocument and sendMessage failed: %s", send_msg_exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"telegram_send_failed: {str(send_msg_exc)}",
            )
    
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="telegram_send_failed",
    )


@router.post("/chat/clear", response_model=ClearChatResponse)
async def clear_chat(payload: ClearChatRequest) -> ClearChatResponse:
    """
    Clear server-side chat session files.
    
    If CHAT_DIR is used, deletes session files. Always returns success.
    """
    chat_store = get_chat_store()
    session_id = payload.session_id
    
    # Try to delete session files if they exist
    try:
        import glob
        chat_dir = chat_store._chat_dir
        pattern = str(chat_dir / f"session-{session_id}-*.jsonl")
        files = glob.glob(pattern)
        deleted_count = 0
        for file_path in files:
            try:
                import os as os_module
                os_module.remove(file_path)
                deleted_count += 1
            except Exception as exc:
                logger.warning("Failed to delete session file %s: %s", file_path, exc)
        if deleted_count > 0:
            logger.info("Cleared %d session files for session=%s", deleted_count, session_id)
    except Exception as exc:
        logger.warning("Failed to clear session files for session=%s: %s", session_id, exc)
        # Don't fail the request - client will clear local state anyway
    
    return ClearChatResponse(ok=True)

