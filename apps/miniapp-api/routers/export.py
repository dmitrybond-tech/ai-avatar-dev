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


def resolve_tg_env() -> tuple[str, List[str]]:
    """Resolve Telegram token and chat IDs from environment variables.
    
    Supports multiple recipients via comma-separated values in:
    - TELEGRAM_ADMIN_CHAT_ID or ADMIN_CHAT_ID
    - TELEGRAM_ADMIN_CHANNEL_ID
    
    Returns: (token, list of chat_ids/usernames)
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
    raw_chat_ids = ",".join(filter(None, [
        os.getenv("TELEGRAM_ADMIN_CHAT_ID") or os.getenv("ADMIN_CHAT_ID"),
        os.getenv("TELEGRAM_ADMIN_CHANNEL_ID"),
    ]))
    
    if not token or not raw_chat_ids:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="telegram_env_missing",
        )
    
    # Support comma-separated ids/usernames
    targets = [x.strip() for x in raw_chat_ids.split(",") if x.strip()]
    if not targets:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="telegram_env_missing",
        )
    
    return token, targets


class ExportTelegramRequest(BaseModel):
    """Request model for Telegram export."""
    session_id: str = Field(..., description="Chat session ID")
    persona: str = Field(default="dima", description="Persona name")
    messages: List[Dict[str, Any]] = Field(..., description="List of messages")
    meta: Optional[Dict[str, Any]] = Field(default=None, description="Metadata")


class SentInfo(BaseModel):
    """Information about a successful send."""
    chat_id: str = Field(..., description="Chat ID or username")
    method: str = Field(..., description="sendDocument or sendMessage")


class ExportTelegramResponse(BaseModel):
    """Response model for Telegram export."""
    ok: bool
    sent: List[SentInfo] = Field(..., description="List of successful sends")
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
    
    Tries sendDocument first (up to ~50MB), falls back to sendMessage (chunked/truncated) if document fails.
    Supports multiple recipients via comma-separated chat IDs in env vars.
    """
    # Resolve Telegram credentials
    try:
        token, chat_ids = resolve_tg_env()
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
        # Cap content length per message
        if len(content) > 10000:
            content = content[:10000] + "...[truncated]"
        # Handle ts: accept ISO string or int timestamp
        ts_value = msg.get("ts")
        if isinstance(ts_value, str):
            try:
                # Try parsing ISO string
                ts_dt = datetime.fromisoformat(ts_value.replace("Z", "+00:00"))
                ts_int = int(ts_dt.timestamp())
            except (ValueError, AttributeError):
                ts_int = int(datetime.now(timezone.utc).timestamp())
        elif isinstance(ts_value, (int, float)):
            ts_int = int(ts_value)
        else:
            ts_int = int(datetime.now(timezone.utc).timestamp())
        
        sanitized_messages.append({
            "role": role,
            "content": content,
            "ts": ts_int,
        })
    
    if not sanitized_messages:
        logger.error("export_telegram.error: empty_messages session=%s", payload.session_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="empty_messages",
        )
    
    # Build export JSON
    export_data: Dict[str, Any] = {
        "export_ts": int(datetime.now(timezone.utc).timestamp()),
        "session_id": payload.session_id,
        "persona": payload.persona,
        "count": len(sanitized_messages),
        "messages": sanitized_messages,
    }
    
    if payload.meta:
        export_data["meta"] = payload.meta
    
    # Apply redaction if enabled
    redact_enabled = os.getenv("REDACT_EXPORT", "false").strip().lower() in {"1", "true", "yes"}
    if redact_enabled:
        export_data = _redact_dict(export_data, enabled=True)
    
    # Serialize to JSON
    json_bytes = json.dumps(export_data, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
    json_size = len(json_bytes)
    
    import httpx
    
    filename = f"chat-export-{payload.session_id}-{int(datetime.now(timezone.utc).timestamp())}.json"
    caption = f"Chat export • session={payload.session_id} • count={len(sanitized_messages)}"
    if len(caption) > 1024:
        caption = caption[:1020] + "..."
    
    sent: List[SentInfo] = []
    last_error: Optional[Dict[str, Any]] = None
    
    # Try to send to each recipient
    for chat_id in chat_ids:
        try:
            # Try sendDocument first (up to ~50MB)
            tg_url_doc = f"https://api.telegram.org/bot{token}/sendDocument"
            async with httpx.AsyncClient(timeout=20.0) as client:
                files = {
                    "document": (filename, json_bytes, "application/json"),
                }
                data = {
                    "chat_id": chat_id,
                    "caption": caption,
                }
                response = await client.post(tg_url_doc, data=data, files=files)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("ok"):
                        sent.append(SentInfo(chat_id=chat_id, method="document"))
                        logger.info("export_telegram.ok: session=%s chat_id=%s method=document size=%d", 
                                   payload.session_id, chat_id, json_size)
                        continue
                
                # Fallback to sendMessage (chunked/truncated)
                json_text = json_bytes.decode("utf-8")
                max_chars = 3800  # Leave room for markdown formatting
                if len(json_text) > max_chars:
                    json_text = json_text[:max_chars] + "\n...[truncated]"
                
                message_text = f"```json\n{json_text}\n```"
                
                tg_url_msg = f"https://api.telegram.org/bot{token}/sendMessage"
                async with httpx.AsyncClient(timeout=20.0) as client:
                    payload_data = {
                        "chat_id": chat_id,
                        "text": message_text[:4096],  # Telegram limit
                        "parse_mode": "Markdown",
                    }
                    response = await client.post(tg_url_msg, json=payload_data)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get("ok"):
                            sent.append(SentInfo(chat_id=chat_id, method="message"))
                            logger.info("export_telegram.ok: session=%s chat_id=%s method=message size=%d", 
                                       payload.session_id, chat_id, json_size)
                            continue
                
                # Both methods failed for this chat_id
                error_text = response.text[:200] if response.text else ""
                last_error = {"chat_id": chat_id, "status": response.status_code, "text": error_text}
                logger.warning("export_telegram.error: session=%s chat_id=%s status=%d", 
                             payload.session_id, chat_id, response.status_code)
                
        except Exception as exc:
            last_error = {"chat_id": chat_id, "exc": str(exc)}
            logger.error("export_telegram.error: session=%s chat_id=%s error=%s", 
                        payload.session_id, chat_id, str(exc), exc_info=True)
    
    # If nothing was sent, raise error
    if not sent:
        logger.error("export_telegram.error: telegram_send_failed session=%s last_error=%s", 
                    payload.session_id, last_error)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"telegram_send_failed": True, "last_error": last_error},
        )
    
    logger.info("export_telegram.ok: session=%s sent=%d recipients size=%d", 
               payload.session_id, len(sent), json_size)
    
    return ExportTelegramResponse(ok=True, sent=sent, bytes=json_size)


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

