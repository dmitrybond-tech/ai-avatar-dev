"""Brief upload endpoints with idempotency and integrations."""
from __future__ import annotations

import hashlib
import logging
import os
import pathlib
import re
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import EmailStr

from apps.miniapp_api.core import env as env_utils
from apps.miniapp_api.services.notion import create_brief_page
from apps.miniapp_api.services.telegram import build_caption, send_brief
from apps.miniapp_api.utils.idempotency import reserve_fp


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/briefs", tags=["briefs"])
alias_router = APIRouter(tags=["briefs-alias"])


ALLOWED = set((os.getenv("ALLOWED_EXT") or "pdf,doc,docx,txt,png,jpg,jpeg,zip").split(","))
DATA_DIR = os.getenv("DATA_DIR", "/data")
UPLOAD_BASE_DIR = os.path.join(DATA_DIR, "uploads")
MAX_MB = int(os.getenv("MAX_UPLOAD_MB", "64"))
MAX_BYTES = MAX_MB * 1024 * 1024
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")

pathlib.Path(UPLOAD_BASE_DIR).mkdir(parents=True, exist_ok=True)


def _sanitize_name(name: str) -> str:
    cleaned = re.sub(r"[^\w\.\-\(\)\s]", "_", name)
    return cleaned[:150] or "file"


def _normalize_phone(phone: str) -> str:
    return re.sub(r"[^\d\+]", "", phone or "")


async def _upload_brief_handler(
    *,
    file: UploadFile,
    locale: str,
    name: str,
    company: str,
    phone: str,
    email: str,
    message: Optional[str],
    request_id: Optional[str],
):
    name = (name or "").strip()
    company = (company or "").strip()
    email = (email or "").strip()
    phone = _normalize_phone(phone)
    locale = (locale or "en").strip().lower() or "en"

    if not (name and company and phone and email):
        raise HTTPException(status_code=422, detail="All fields are required")

    if "@" not in email:
        raise HTTPException(status_code=422, detail="Invalid email")

    ext = (pathlib.Path(file.filename or "").suffix or "").lstrip(".").lower()
    if ext not in ALLOWED:
        raise HTTPException(
            status_code=400,
            detail=f"Extension .{ext} not allowed. Allowed: {', '.join(sorted(ALLOWED))}",
        )

    file_bytes = await file.read()
    await file.close()

    if len(file_bytes) > MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large. Max size: {MAX_MB} MB")

    file_hash = hashlib.sha256(file_bytes).hexdigest()
    fingerprint_src = f"{email}|{name}|{company}|{phone}|{file_hash}"
    fingerprint = hashlib.sha256(fingerprint_src.encode("utf-8")).hexdigest()

    is_new, reserved_request_id = await reserve_fp(fingerprint, request_id)

    if not is_new:
        logger.info("Duplicate brief submission detected: %s", reserved_request_id)
        return JSONResponse(
            {
                "ok": True,
                "request_id": reserved_request_id,
                "notion_page_id": None,
                "dedup": True,
            }
        )

    safe_filename = _sanitize_name(file.filename or "file")
    upload_dir = pathlib.Path(UPLOAD_BASE_DIR) / reserved_request_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / safe_filename
    file_path.write_bytes(file_bytes)

    logger.info("Stored brief upload for request %s", reserved_request_id)

    telegram_sent = False
    if BOT_TOKEN and ADMIN_CHAT_ID:
        try:
            admin_chat_id_int = int(str(ADMIN_CHAT_ID).strip())
            caption = build_caption(
                request_id=reserved_request_id,
                locale=locale,
                name=name,
                company=company,
                phone=phone,
                email=email,
                message=message,
            )
            telegram_sent = await send_brief(
                admin_chat_id=admin_chat_id_int,
                bot_token=BOT_TOKEN,
                path_to_file=str(file_path),
                caption=caption,
            )
        except ValueError:
            logger.error("Invalid TELEGRAM_ADMIN_CHAT_ID; skipping Telegram send")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Telegram send failed for request %s: %s", reserved_request_id, exc.__class__.__name__)

    notion_page_id = None
    notion_token = env_utils.notion_token() or ""
    notion_db_id = env_utils.tasks_db() or ""
    if notion_token and notion_db_id:
        try:
            notion_page_id = await create_brief_page(
                notion_token=notion_token,
                db_id=notion_db_id,
                data={
                    "request_id": reserved_request_id,
                    "name": name,
                    "company": company,
                    "phone": phone,
                    "email": email,
                    "locale": locale,
                    "message": message or "",
                    "telegram_sent": telegram_sent,
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Notion create failed for request %s: %s", reserved_request_id, exc.__class__.__name__)

    return JSONResponse(
        {
            "ok": True,
            "request_id": reserved_request_id,
            "notion_page_id": notion_page_id,
            "dedup": False,
        }
    )


@router.post("/upload")
async def upload_brief(
    file: UploadFile = File(...),
    locale: str = Form("en"),
    name: str = Form(...),
    company: str = Form(...),
    phone: str = Form(...),
    email: EmailStr = Form(...),
    message: Optional[str] = Form(None),
    request_id: Optional[str] = Form(None),
):
    return await _upload_brief_handler(
        file=file,
        locale=locale,
        name=name,
        company=company,
        phone=phone,
        email=email,
        message=message,
        request_id=request_id,
    )


@alias_router.post("/api/briefs/upload")
async def upload_brief_alias(
    file: UploadFile = File(...),
    locale: str = Form("en"),
    name: str = Form(...),
    company: str = Form(...),
    phone: str = Form(...),
    email: EmailStr = Form(...),
    message: Optional[str] = Form(None),
    request_id: Optional[str] = Form(None),
):
    return await _upload_brief_handler(
        file=file,
        locale=locale,
        name=name,
        company=company,
        phone=phone,
        email=email,
        message=message,
        request_id=request_id,
    )


