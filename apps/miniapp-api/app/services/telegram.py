from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Iterable, List, Optional

import httpx

from ..models.chat import ChatMessage

logger = logging.getLogger(__name__)

MD_V2_SPECIALS = set(r"_*[]()~`>#+-=|{}.!")


def escape_markdown(text: str) -> str:
    return "".join(f"\\{ch}" if ch in MD_V2_SPECIALS else ch for ch in text)


def format_transcript(messages: Iterable[ChatMessage], meta: Optional[Dict[str, Any]] = None, title: Optional[str] = None) -> str:
    lines: List[str] = []
    header = title or "Chat transcript"
    lines.append(f"*{escape_markdown(header)}*")
    if meta:
        meta_lines = ["*Meta:*"]
        for key, value in meta.items():
            rendered = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
            meta_lines.append(f"- {escape_markdown(str(key))}: {escape_markdown(rendered)}")
        lines.append("\n".join(meta_lines))
    for message in messages:
        prefix = {
            "user": "👤 User",
            "assistant": "🤖 Assistant",
            "system": "⚙️ System",
        }.get(message.role, "💬 Message")
        body = escape_markdown(message.content)
        lines.append(f"*{prefix}:* {body}")
    return "\n\n".join(lines)


def _chunk_text(text: str, limit: int = 4096) -> List[str]:
    """Split text into chunks respecting line boundaries."""
    chunks: List[str] = []
    current = ""
    for line in text.splitlines():
        if len(current) + len(line) + 1 > limit:
            if current:
                chunks.append(current)
            current = line
        else:
            current = (current + "\n" + line) if current else line
    if current:
        chunks.append(current)
    return chunks if chunks else [text]


class TelegramExporter:
    def __init__(self) -> None:
        # Env with backward-compatible fallbacks
        self._token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
        self._chat_id = os.getenv("ADMIN_CHAT_ID") or os.getenv("TELEGRAM_ADMIN_CHAT_ID")
        timeout_raw = os.getenv("TELEGRAM_TIMEOUT") or ""
        try:
            self._timeout = float(timeout_raw) if timeout_raw else 15.0
        except ValueError:
            self._timeout = 15.0

    @property
    def available(self) -> bool:
        return bool(self._token and self._chat_id)

    async def _tg_api(
        self,
        method: str,
        payload: Dict[str, Any],
        files: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Call Telegram Bot API with error handling."""
        if not self._token:
            raise ValueError("TELEGRAM_TOKEN is not set")
        url = f"https://api.telegram.org/bot{self._token}/{method}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            if files:
                response = await client.post(url, data=payload, files=files)
            else:
                response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram error: {data}")
        return data

    async def selftest(self) -> Dict[str, Any]:
        """Test Telegram bot token by calling getMe."""
        if not self._token:
            raise ValueError("TELEGRAM_TOKEN is not set")
        data = await self._tg_api("getMe", {})
        return {"ok": True, "bot": data.get("result", {})}

    async def send(
        self,
        messages: List[ChatMessage],
        *,
        meta: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        if dry_run or not self.available:
            logger.info("Telegram export dry-run or unavailable (dry_run=%s, available=%s)", dry_run, self.available)
            return {"ok": True, "message_id": "dry_run", "sent": {"method": "dry_run"}}

        if not self._chat_id:
            raise ValueError("ADMIN_CHAT_ID is not set")

        transcript = format_transcript(messages, meta=meta, title=title)
        if not transcript:
            return {"ok": False, "error": "empty_transcript"}

        # For short messages (≤3500 chars), use sendMessage with chunking if needed
        # For longer messages, use sendDocument
        if len(transcript) <= 3500:
            chunks = _chunk_text(transcript, limit=4096)
            sent_count = 0
            for chunk in chunks:
                payload = {
                    "chat_id": self._chat_id,
                    "text": chunk,
                    "parse_mode": "MarkdownV2",
                    "disable_web_page_preview": True,
                }
                await self._tg_api("sendMessage", payload)
                sent_count += 1
            message_id = None  # Multiple messages, no single ID
            return {"ok": True, "sent": {"method": "sendMessage", "parts": sent_count}}
        else:
            # Use sendDocument for large transcripts
            transcript_bytes = transcript.encode("utf-8")
            filename = (title or "conversation") + ".txt"
            files = {"document": (filename, transcript_bytes, "text/plain; charset=utf-8")}
            payload = {
                "chat_id": self._chat_id,
                "caption": title or "",
            }
            data = await self._tg_api("sendDocument", payload, files=files)
            message_id = data.get("result", {}).get("message_id")
            return {"ok": True, "message_id": message_id, "sent": {"method": "sendDocument"}}

