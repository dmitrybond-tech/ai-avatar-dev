"""Idempotency utilities for brief uploads."""
import os
import time
from datetime import datetime
from typing import Tuple, Optional
from redis import Redis
from ulid import ULID
from app.core.logging import get_logger

logger = get_logger(__name__)

TTL_SEC = int(os.getenv("BRIEF_IDEMPOTENCY_TTL", "900"))  # 15 minutes default
REDIS_URL = os.getenv("REDIS_URL")
DATA_DIR = os.getenv("DATA_DIR", "/data")
BRIEF_IDS_DIR = os.path.join(DATA_DIR, "brief-ids")


def new_request_id() -> str:
    """Generate a new request ID in format BRF-YYYYMMDD-ULID."""
    date_str = datetime.utcnow().strftime("%Y%m%d")
    ulid = str(ULID())
    return f"BRF-{date_str}-{ulid}"


async def reserve_fp(
    fingerprint: str,
    incoming_request_id: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Reserve a fingerprint for idempotency.
    
    Args:
        fingerprint: SHA256 fingerprint of the request
        incoming_request_id: Optional request ID to use (if provided)
    
    Returns:
        Tuple of (is_new, request_id):
        - is_new: True if this is a new request, False if duplicate
        - request_id: The request ID (existing or newly generated)
    """
    request_id = incoming_request_id or new_request_id()
    
    if REDIS_URL:
        # Use Redis for idempotency
        try:
            r = Redis.from_url(REDIS_URL, decode_responses=True)
            # Try to set the key (only if it doesn't exist)
            ok = r.set(f"brief:fp:{fingerprint}", request_id, nx=True, ex=TTL_SEC)
            
            if ok:
                # Successfully created new entry
                logger.info(f"New brief fingerprint reserved: {fingerprint[:16]}... -> {request_id}")
                return True, request_id
            else:
                # Key already exists, get the existing request_id
                existing_id = r.get(f"brief:fp:{fingerprint}")
                if existing_id:
                    logger.info(f"Duplicate brief detected: {fingerprint[:16]}... -> {existing_id}")
                    return False, existing_id
                else:
                    # Race condition: key was deleted between check and get
                    # Try again with a new request_id
                    request_id = new_request_id()
                    ok = r.set(f"brief:fp:{fingerprint}", request_id, nx=True, ex=TTL_SEC)
                    if ok:
                        return True, request_id
                    existing_id = r.get(f"brief:fp:{fingerprint}")
                    return False, existing_id or request_id
        except Exception as e:
            logger.warning(f"Redis idempotency failed, falling back to FS: {e}")
            # Fall through to file-based approach
    
    # File-based fallback
    os.makedirs(BRIEF_IDS_DIR, exist_ok=True)
    path = os.path.join(BRIEF_IDS_DIR, fingerprint)
    
    try:
        # Try to create file exclusively (atomic operation)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, request_id.encode("utf-8"))
            os.close(fd)
            logger.info(f"New brief fingerprint reserved (FS): {fingerprint[:16]}... -> {request_id}")
            return True, request_id
        except Exception:
            os.close(fd)
            raise
    except FileExistsError:
        # File already exists, read the existing request_id
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing_id = f.read().strip()
            logger.info(f"Duplicate brief detected (FS): {fingerprint[:16]}... -> {existing_id}")
            return False, existing_id
        except Exception as e:
            logger.error(f"Failed to read existing fingerprint file: {e}")
            # Return the new request_id as fallback
            return True, request_id

