"""Brief upload router."""
from __future__ import annotations

import logging
import os
import pathlib
import re
import uuid
from typing import Optional

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

router = APIRouter(prefix="/briefs", tags=["briefs"])

logger = logging.getLogger(__name__)

DEFAULT_ALLOWED_EXT = ("pdf", "doc", "docx", "txt", "png", "jpg", "jpeg", "zip")
ALLOWED_EXT = {
    ext.strip().lower()
    for ext in (os.getenv("ALLOWED_EXT") or ",".join(DEFAULT_ALLOWED_EXT)).split(",")
    if ext.strip()
}

ALLOWED_MIME = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "application/zip",
    "application/x-zip-compressed",
    "image/png",
    "image/jpeg",
}

UPLOAD_DIR = pathlib.Path(os.getenv("UPLOAD_DIR", "/app/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_MB = int(os.getenv("MAX_UPLOAD_MB", "25"))
MAX_BYTES = MAX_MB * 1024 * 1024
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_CHAT = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
TELEGRAM_REQUIRED = os.getenv("TELEGRAM_SEND_REQUIRED", "false").lower() in {"1", "true", "yes"}


def _sanitize_name(name: str) -> str:
    sanitized = re.sub(r"[^\w\.\-\(\)\s]", "_", name)
    return sanitized[:150] or "file"


def _normalize_content_type(value: Optional[str]) -> str:
    if not value:
        return ""
    return value.split(";")[0].strip().lower()


@router.post("/upload")
async def upload_brief(
    file: UploadFile = File(...),
    locale: Optional[str] = Form(default=None),
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    company: str = Form(...),
    comment: str = Form(default="", alias="comment"),
    message: str = Form(default="", alias="message"),
):
    """Upload a brief file, persist it, and optionally forward to Telegram."""

    note = comment or message

    ext = (pathlib.Path(file.filename or "").suffix or "").lstrip(".").lower()
    if ext not in ALLOWED_EXT:
        allowed = ", ".join(sorted(ALLOWED_EXT))
        raise HTTPException(status_code=400, detail=f"unsupported-extension:{ext}" if ext else "missing-extension")

    content_type = _normalize_content_type(file.content_type)
    if content_type and content_type not in ALLOWED_MIME:
        raise HTTPException(status_code=415, detail="unsupported-content-type")

    safe_original = _sanitize_name(file.filename or "file")
    stored_name = f"{uuid.uuid4().hex}_{safe_original}"
    dest = UPLOAD_DIR / stored_name

    size = 0
    try:
        with dest.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 128)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_BYTES:
                    out.close()
                    dest.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail=f"File too large. Max size: {MAX_MB} MB")
                out.write(chunk)
    finally:
        await file.close()

    telegram_sent = False
    if BOT_TOKEN and ADMIN_CHAT:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
            caption_lines = [
                f"Brief upload ({locale or 'en'})",
                f"Name: {name}",
                f"Email: {email}",
                f"Phone: {phone}",
                f"Company: {company}",
            ]
            if note:
                caption_lines.append(f"Comment: {note[:400]}")
            caption_lines.append(f"File: {safe_original} ({round(size / 1024 / 1024, 2)} MB)")
            caption = "\n".join(caption_lines)

            async with httpx.AsyncClient(timeout=60.0) as client:
                with dest.open("rb") as fh:
                    data = {"chat_id": ADMIN_CHAT, "caption": caption[:1024]}
                    files = {
                        "document": (
                            safe_original,
                            fh,
                            content_type or "application/octet-stream",
                        )
                    }
                    response = await client.post(url, data=data, files=files)
                    response.raise_for_status()
                    telegram_sent = True
        except Exception as exc:  # noqa: BLE001 - we need to tolerate Telegram outages
            logger.warning("Telegram delivery failed: %s", exc, exc_info=True)
            if TELEGRAM_REQUIRED:
                raise HTTPException(status_code=502, detail="telegram-send-failed")

    logger.info(
        "brief_saved",
        extra={
            "brief_filename": safe_original,
            "brief_stored_as": stored_name,
            "brief_bytes": size,
            "brief_telegram_sent": telegram_sent,
        },
    )

    return {
        "ok": True,
        "saved": True,
        "filename": safe_original,
        "bytes": size,
        "telegram_sent": telegram_sent,
    }

