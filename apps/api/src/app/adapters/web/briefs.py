"""Brief upload router."""
import os
import time
import pathlib
import re
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import httpx
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/briefs", tags=["briefs"])

ALLOWED = set((os.getenv("ALLOWED_EXT") or "pdf,doc,docx,txt,png,jpg,jpeg,zip").split(","))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads/briefs")
MAX_MB = int(os.getenv("MAX_UPLOAD_MB", "25"))
MAX_BYTES = MAX_MB * 1024 * 1024
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_CHAT = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")

# Ensure upload directory exists
pathlib.Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


def _sanitize_name(name: str) -> str:
    """Sanitize filename for safe storage."""
    name = re.sub(r"[^\w\.\-\(\)\s]", "_", name)
    return name[:150] or "file"


@router.post("/upload")
async def upload_brief(file: UploadFile = File(...), locale: str = Form(None)):
    """Upload a brief file and forward it to Telegram admin."""
    # Check file extension
    ext = (pathlib.Path(file.filename or "").suffix or "").lstrip(".").lower()
    if ext not in ALLOWED:
        raise HTTPException(status_code=400, detail=f"Extension .{ext} not allowed. Allowed: {', '.join(sorted(ALLOWED))}")

    # Sanitize filename
    safe = _sanitize_name(file.filename or "file")
    ts = int(time.time())
    dest = os.path.join(UPLOAD_DIR, f"{ts}_{safe}")

    # Stream write and check size
    size = 0
    try:
        with open(dest, "wb") as out:
            while True:
                chunk = await file.read(1024 * 64)  # 64KB chunks
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_BYTES:
                    out.close()
                    os.remove(dest)
                    raise HTTPException(status_code=413, detail=f"File too large. Max size: {MAX_MB} MB")
                out.write(chunk)
    finally:
        await file.close()

    # Forward to Telegram admin
    telegram_sent = False
    if BOT_TOKEN and ADMIN_CHAT:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
            caption = f"New brief ({locale or 'en'}): {safe} ({round(size/1024/1024, 2)} MB)"
            async with httpx.AsyncClient(timeout=60.0) as client:
                with open(dest, "rb") as fh:
                    data = {"chat_id": ADMIN_CHAT, "caption": caption}
                    files = {"document": (safe, fh, file.content_type or "application/octet-stream")}
                    r = await client.post(url, data=data, files=files)
                    if r.status_code >= 400:
                        logger.warning(f"Telegram send failed: {r.status_code} {r.text}")
                    else:
                        telegram_sent = True
        except Exception as e:
            logger.error(f"Failed to send to Telegram: {e}", exc_info=True)
            # Don't fail the request if Telegram fails

    return {
        "ok": True,
        "saved": True,
        "filename": safe,
        "bytes": size,
        "telegram_sent": telegram_sent,
    }

