"""Idempotency utilities for brief uploads."""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional, Tuple

from redis import Redis
from ulid import ULID


logger = logging.getLogger(__name__)

TTL_SEC = int(os.getenv("BRIEF_IDEMPOTENCY_TTL", "900"))
REDIS_URL = os.getenv("REDIS_URL")
DATA_DIR = os.getenv("DATA_DIR", "/data")
BRIEF_IDS_DIR = os.path.join(DATA_DIR, "brief-ids")


def new_request_id() -> str:
    """Generate a new request ID with BRF prefix."""
    date_str = datetime.utcnow().strftime("%Y%m%d")
    ulid = str(ULID())
    return f"BRF-{date_str}-{ulid}"


async def reserve_fp(
    fingerprint: str,
    incoming_request_id: Optional[str] = None,
) -> Tuple[bool, str]:
    """Reserve fingerprint to enforce idempotency.

    Returns a tuple of (is_new, request_id) where is_new indicates whether the
    fingerprint was newly registered.
    """

    request_id = incoming_request_id or new_request_id()

    if REDIS_URL:
        try:
            def _redis_check() -> Tuple[bool, str, None]:
                redis = Redis.from_url(REDIS_URL, decode_responses=True)
                key = f"brief:fp:{fingerprint}"
                ok = redis.set(key, request_id, nx=True, ex=TTL_SEC)
                if ok:
                    return True, request_id, None

                existing_id = redis.get(key)
                if existing_id:
                    return False, existing_id, None

                new_id = new_request_id()
                ok_retry = redis.set(key, new_id, nx=True, ex=TTL_SEC)
                if ok_retry:
                    return True, new_id, None

                existing_id_retry = redis.get(key)
                return False, existing_id_retry or new_id, None

            is_new, reserved_id, _ = await asyncio.to_thread(_redis_check)
            if is_new:
                logger.info("Reserved new brief fingerprint via redis: %s", reserved_id)
                return True, reserved_id

            logger.info("Deduplicated brief fingerprint via redis: %s", reserved_id)
            return False, reserved_id
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis idempotency check failed, falling back to FS: %s", exc.__class__.__name__)

    os.makedirs(BRIEF_IDS_DIR, exist_ok=True)
    path = os.path.join(BRIEF_IDS_DIR, fingerprint)

    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, request_id.encode("utf-8"))
        finally:
            os.close(fd)
        logger.info("Reserved new brief fingerprint via filesystem: %s", request_id)
        return True, request_id
    except FileExistsError:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                existing_id = handle.read().strip()
            logger.info("Deduplicated brief fingerprint via filesystem: %s", existing_id)
            return False, existing_id or request_id
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to read existing fingerprint entry: %s", exc.__class__.__name__)
            return True, request_id


