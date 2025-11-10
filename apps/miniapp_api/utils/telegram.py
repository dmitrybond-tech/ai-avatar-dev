from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Optional
from urllib.parse import parse_qsl

import httpx

logger = logging.getLogger(__name__)


def verify_webapp_initdata(init_data: str, bot_token: str) -> Optional[int]:
    if not init_data or not bot_token:
        return None

    params = dict(parse_qsl(init_data, keep_blank_values=True))
    provided_hash = params.pop("hash", None)
    if not provided_hash:
        return None

    data_check_items = [f"{k}={v}" for k, v in sorted(params.items())]
    data_check_string = "\n".join(data_check_items)

    secret_key = hmac.new(
        key="WebAppData".encode("utf-8"),
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if calculated_hash != provided_hash:
        logger.warning("Telegram init data verification failed: hash mismatch")
        return None

    user_json = params.get("user")
    if not user_json:
        return None
    try:
        user_data = json.loads(user_json)
    except json.JSONDecodeError:
        logger.warning("Telegram init data malformed user payload")
        return None

    user_id = user_data.get("id")
    if isinstance(user_id, int):
        return user_id
    if isinstance(user_id, str) and user_id.isdigit():
        return int(user_id)
    return None


async def send_message(token: str, chat_id: int, text: str) -> bool:
    if not token or not chat_id or not text.strip():
        logger.debug("Telegram send skipped: missing token/chat_id/text")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload)
    except httpx.TimeoutException:
        logger.warning("Telegram sendMessage timeout")
        return False
    except Exception as exc:  # noqa: BLE001 - external call
        logger.warning("Telegram sendMessage failed: %s", exc)
        return False

    if response.status_code >= 400:
        logger.warning("Telegram sendMessage HTTP %s", response.status_code)
        return False

    try:
        data = response.json()
    except ValueError:
        logger.warning("Telegram sendMessage: invalid JSON response")
        return False

    success = bool(data.get("ok"))
    if not success:
        logger.warning("Telegram sendMessage returned ok=false: %s", data)
    return success

