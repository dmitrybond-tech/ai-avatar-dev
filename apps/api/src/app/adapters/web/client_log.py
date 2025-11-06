"""Client log/telemetry endpoint (minimal, optional)."""
from fastapi import APIRouter, Request, Response, Body
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/client-log")
async def client_log(payload: Dict[str, Any] = Body(...)) -> JSONResponse:
    """Accept minimal client-side logs and write to server logs.
    
    Accepts JSON with: level (info/warn/error), message, extra (dict), ua (string).
    Returns {ok: true} on success.
    """
    try:
        level = payload.get("level", "info").lower()
        msg = payload.get("message", "")
        extra = {k: v for k, v in payload.items() if k not in ("level", "message")}
        
        # Use appropriate log level
        log_level = level if level in ("info", "warning", "error") else "info"
        getattr(logger, log_level)(f"client-log: {msg} | {extra}")
    except Exception as e:  # pragma: no cover - best effort logging
        logger.error("client-log failed: %s", e)
    return JSONResponse({"ok": True})


@router.post("/api/client-log")
async def client_log_alias(payload: Dict[str, Any] = Body(...)) -> JSONResponse:
    """Backward-compat alias for /client-log."""
    return await client_log(payload)


