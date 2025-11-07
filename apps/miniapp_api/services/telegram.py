"""Telegram service helpers for miniapp brief uploads."""
from __future__ import annotations

import logging
import os

import httpx


logger = logging.getLogger(__name__)


async def send_brief(
    admin_chat_id: int,
    bot_token: str,
    path_to_file: str,
    caption: str,
) -> bool:
    """Send uploaded brief to Telegram admin chat."""
    if not admin_chat_id or not bot_token:
        logger.warning("Telegram credentials missing; skipping send")
        return False

    if not os.path.exists(path_to_file):
        logger.error("Telegram send failed: file not found")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            with open(path_to_file, "rb") as handle:
                file_name = os.path.basename(path_to_file)
                data = {
                    "chat_id": admin_chat_id,
                    "caption": caption,
                    "parse_mode": "HTML",
                }
                files = {"document": (file_name, handle, "application/octet-stream")}
                response = await client.post(url, data=data, files=files)

        if response.status_code < 400:
            logger.info("Brief uploaded to Telegram admin: %s", file_name)
            return True

        logger.warning("Telegram send failed: status=%s", response.status_code)
    except Exception as exc:  # noqa: BLE001
        logger.error("Telegram send exception: %s", exc, exc_info=True)

    return False


def build_caption(
    request_id: str,
    locale: str,
    name: str,
    company: str,
    phone: str,
    email: str,
    message: str | None = None,
) -> str:
    """Compose HTML caption without leaking PII to logs."""
    import html

    parts = [
        f"<b>New Brief</b> ({html.escape(locale.upper())})",
        f"<b>Request ID:</b> {html.escape(request_id)}",
        f"<b>Name:</b> {html.escape(name)}",
        f"<b>Company:</b> {html.escape(company)}",
        f"<b>Phone:</b> {html.escape(phone)}",
        f"<b>Email:</b> {html.escape(email)}",
    ]

    if message and message.strip():
        parts.append(f"<b>Comment:</b> {html.escape(message.strip())}")

    return "\n".join(parts)


