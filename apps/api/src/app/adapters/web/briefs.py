"""Brief upload router."""
import os
import hashlib
import pathlib
import re
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import EmailStr
from app.core.logging import get_logger
from app.utils.idempotency import reserve_fp
from app.services.telegram import send_brief, build_caption
from app.services.notion import create_brief_page

logger = get_logger(__name__)

router = APIRouter(prefix="/briefs", tags=["briefs"])

ALLOWED = set((os.getenv("ALLOWED_EXT") or "pdf,doc,docx,txt,png,jpg,jpeg,zip").split(","))
DATA_DIR = os.getenv("DATA_DIR", "/data")
UPLOAD_BASE_DIR = os.path.join(DATA_DIR, "uploads")
MAX_MB = int(os.getenv("MAX_UPLOAD_MB", "64"))
MAX_BYTES = MAX_MB * 1024 * 1024
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
NOTION_TOKEN = os.getenv("NOTION_API_KEY", "")
NOTION_DB_ID = os.getenv("NOTION_PUBLIC_TASKS_DB_ID", "")

# Ensure upload base directory exists
pathlib.Path(UPLOAD_BASE_DIR).mkdir(parents=True, exist_ok=True)


def _sanitize_name(name: str) -> str:
    """Sanitize filename for safe storage."""
    name = re.sub(r"[^\w\.\-\(\)\s]", "_", name)
    return name[:150] or "file"


def _is_email(v: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v or "", re.I))


async def _upload_brief_handler(
    file: UploadFile,
    locale: str,
    name: str,
    company: str,
    phone: str,
    email: str,
    message: str | None = None,
    request_id: str | None = None,
):
    """Internal handler for brief upload."""
    # Validate and sanitize inputs
    name = (name or "").strip()
    company = (company or "").strip()
    phone = re.sub(r"[^\d\+]", "", phone or "")
    email = (email or "").strip()
    locale = (locale or "en").strip().lower()
    
    if not (name and company and phone and email):
        raise HTTPException(status_code=422, detail="All fields are required")
    if not _is_email(email):
        raise HTTPException(status_code=422, detail="Invalid email")
    
    # Check file extension
    ext = (pathlib.Path(file.filename or "").suffix or "").lstrip(".").lower()
    if ext not in ALLOWED:
        raise HTTPException(
            status_code=400,
            detail=f"Extension .{ext} not allowed. Allowed: {', '.join(sorted(ALLOWED))}"
        )
    
    # Read file and compute hash
    file_bytes = await file.read()
    await file.close()
    
    if len(file_bytes) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {MAX_MB} MB"
        )
    
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    
    # Compute fingerprint: sha256(email|name|company|phone|file_hash)
    fp_src = f"{email}|{name}|{company}|{phone}|{file_hash}"
    fingerprint = hashlib.sha256(fp_src.encode("utf-8")).hexdigest()
    
    # Check idempotency
    is_new, request_id = await reserve_fp(fingerprint, request_id)
    
    # If duplicate, return early without processing
    if not is_new:
        logger.info(f"Duplicate brief request detected: {request_id}")
        return JSONResponse({
            "ok": True,
            "request_id": request_id,
            "notion_page_id": None,
            "dedup": True,
        })
    
    # New request - process it
    logger.info(f"Processing new brief request: {request_id}")
    
    # Save file to /data/uploads/{request_id}/{safe_filename}
    safe_filename = _sanitize_name(file.filename or "file")
    upload_dir = pathlib.Path(UPLOAD_BASE_DIR) / request_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / safe_filename
    file_path.write_bytes(file_bytes)
    
    # Send to Telegram
    caption = build_caption(request_id, locale, name, company, phone, email, message)
    telegram_sent = False
    if ADMIN_CHAT_ID and BOT_TOKEN:
        try:
            admin_chat_id_int = int(ADMIN_CHAT_ID)
            telegram_sent = await send_brief(
                admin_chat_id=admin_chat_id_int,
                bot_token=BOT_TOKEN,
                path_to_file=str(file_path),
                caption=caption,
            )
        except (ValueError, Exception) as e:
            logger.warning(f"Failed to send to Telegram: {e}")
    
    # Create Notion page
    notion_page_id = None
    if NOTION_TOKEN and NOTION_DB_ID:
        try:
            notion_page_id = await create_brief_page(
                notion_token=NOTION_TOKEN,
                db_id=NOTION_DB_ID,
                data={
                    "request_id": request_id,
                    "name": name,
                    "company": company,
                    "phone": phone,
                    "email": email,
                    "locale": locale,
                    "message": message or "",
                },
            )
        except Exception as e:
            logger.warning(f"Failed to create Notion page: {e}")
    
    return JSONResponse({
        "ok": True,
        "request_id": request_id,
        "notion_page_id": notion_page_id,
        "dedup": False,
    })


@router.post("/upload")
async def upload_brief(
    file: UploadFile = File(...),
    locale: str = Form("en"),
    name: str = Form(...),
    company: str = Form(...),
    phone: str = Form(...),
    email: EmailStr = Form(...),
    message: str | None = Form(None),
    request_id: str | None = Form(None),
):
    """Upload a brief file, save it, and forward to Telegram admin and Notion."""
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


# Alias router for /api/briefs/upload (without prefix)
alias_router = APIRouter(tags=["briefs"])


@alias_router.post("/api/briefs/upload")
async def upload_brief_alias(
    file: UploadFile = File(...),
    locale: str = Form("en"),
    name: str = Form(...),
    company: str = Form(...),
    phone: str = Form(...),
    email: EmailStr = Form(...),
    message: str | None = Form(None),
    request_id: str | None = Form(None),
):
    """Alias for /briefs/upload to support /api/briefs/upload route."""
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
