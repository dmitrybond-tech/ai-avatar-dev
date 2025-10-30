"""Client log/telemetry endpoint (minimal, optional)."""
from fastapi import APIRouter, Request, Response
from pydantic import BaseModel
from typing import Optional
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class ClientLog(BaseModel):
    ua: str
    location: str
    message: str
    stack: Optional[str] = None


@router.post("/api/client-log", status_code=204)
async def client_log(payload: ClientLog, request: Request) -> Response:
    """Accept minimal client-side error logs and write to server logs.

    Always returns 204 to avoid leaking details to the client.
    """
    try:
        logger.warning(
            "client-log: %s | %s | %s | %s",
            payload.ua,
            payload.location,
            payload.message,
            (payload.stack or ""),
        )
    except Exception as e:  # pragma: no cover - best effort logging
        logger.error("client-log failed: %s", e)
    return Response(status_code=204)


