from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Iterable, List, Optional

import httpx

from apps.miniapp_api.models.chat_io import ChatMessagePayload


logger = logging.getLogger(__name__)

MD_V2_SPECIALS = set(r"_*[]()~`>#+-=|{}.!")  # Telegram Markdown v2 reserved chars


def _escape_markdown(text: str) -> str:
    return "".join(f"\\{ch}" if ch in MD_V2_SPECIALS else ch for ch in text)


def _format_transcript(
    messages: Iterable[ChatMessagePayload],
    meta: Optional[Dict[str, Any]] = None,
    title: Optional[str] = None,
) -> str:
    lines: List[str] = []
    header = title or "Chat transcript"
    lines.append(f"*{_escape_markdown(header)}*")
    if meta:
        meta_lines = ["*Meta:*"]
        for key, value in meta.items():
            rendered = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
            meta_lines.append(f"- {_escape_markdown(str(key))}: {_escape_markdown(rendered)}")
        lines.append("\n".join(meta_lines))
    for message in messages:
        prefix = {
            "user": "👤 User",
            "assistant": "🤖 Assistant",
            "system": "⚙️ System",
        }.get(message.role, "💬 Message")
        body = _escape_markdown(message.content)
        lines.append(f"*{prefix}:* {body}")
    return "\n\n".join(lines)


class TelegramExporter:
    def __init__(self) -> None:
        self._token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
        self._chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID") or os.getenv("ADMIN_CHAT_ID")
        timeout_raw = os.getenv("TELEGRAM_TIMEOUT") or ""
        try:
            self._timeout = float(timeout_raw) if timeout_raw else 10.0
        except ValueError:
            self._timeout = 10.0

    @property
    def available(self) -> bool:
        return bool(self._token and self._chat_id)

    async def send(
        self,
        messages: List[ChatMessagePayload],
        *,
        meta: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        if dry_run or not self.available:
            logger.info("telegram_export skip dry_run=%s available=%s", dry_run, self.available)
            return {"ok": True, "message_id": "dry_run"}

        transcript = _format_transcript(messages, meta=meta, title=title)
        if not transcript:
            return {"ok": False, "error": "empty_transcript"}

        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        payload = {
            "chat_id": self._chat_id,
            "text": transcript,
            "parse_mode": "MarkdownV2",
            "disable_web_page_preview": True,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=payload)

        try:
            response.raise_for_status()
            data = response.json()
        except Exception as exc:  # pragma: no cover - network failure
            logger.error("telegram_export_failed error=%s", exc)
            raise
        if not data.get("ok"):
            logger.error("telegram_export_error response=%s", data)
            raise RuntimeError("telegram_error")
        message_id = data.get("result", {}).get("message_id")
        return {"ok": True, "message_id": message_id}


