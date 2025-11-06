"""Brief upload router."""
import os
import time
import pathlib
import re
import html
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


def _is_email(v: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v or "", re.I))


@router.post("/upload")
async def upload_brief(
    file: UploadFile = File(...),
    locale: str = Form(None),
    name: str = Form(...),
    company: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    message: str | None = Form(None),
):
    """Upload a brief file, save it, and forward digest + file to Telegram admin."""
    name = (name or "").strip()
    company = (company or "").strip()
    phone = re.sub(r"[^\d\+]", "", phone or "")
    email = (email or "").strip()
    if not (name and company and phone and email):
        raise HTTPException(status_code=422, detail="All fields are required")
    if not _is_email(email):
        raise HTTPException(status_code=422, detail="Invalid email")
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

    # Forward digest and document to Telegram admin
    telegram_sent = False
    if BOT_TOKEN and ADMIN_CHAT:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # 1) Send digest message
                message_text = ""
                if message and message.strip():
                    # HTML escape the message for safety
                    message_escaped = html.escape(message.strip())
                    message_text = f"<b>Comment:</b> {message_escaped}\n"
                text = (
                    f"<b>New brief</b> ({(locale or 'en').upper()})\n"
                    f"<b>Name:</b> {name}\n"
                    f"<b>Company:</b> {company}\n"
                    f"<b>Phone:</b> {phone}\n"
                    f"<b>Email:</b> {email}\n"
                    + message_text
                    + f"<b>File:</b> {safe} ({round(size/1024/1024, 2)} MB)"
                )
                sm_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                _sm = await client.post(sm_url, data={"chat_id": ADMIN_CHAT, "text": text, "parse_mode": "HTML"})

                # 2) Send file as document
                sd_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
                with open(dest, "rb") as fh:
                    data = {"chat_id": ADMIN_CHAT, "caption": f"{safe}"}
                    files = {"document": (safe, fh, file.content_type or "application/octet-stream")}
                    _sd = await client.post(sd_url, data=data, files=files)

                if (_sm.status_code < 400) or (_sd.status_code < 400):
                    telegram_sent = True
                else:
                    logger.warning(
                        f"Telegram send failed: message={_sm.status_code} file={_sd.status_code}"
                    )
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

