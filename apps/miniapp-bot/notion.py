import os
import logging
from typing import Any
import httpx


logger = logging.getLogger("miniapp-bot")


class NotionClient:
    def __init__(self) -> None:
        self._secret = os.getenv("NOTION_SECRET", "")
        self._db = os.getenv("NOTION_DB", "")
        if not self._secret or not self._db:
            logger.warning("Notion is not fully configured: NOTION_SECRET/NOTION_DB missing")

    def configured(self) -> bool:
        return bool(self._secret and self._db)

    async def create_brief_page(self, payload: dict[str, Any]) -> str | None:
        if not self.configured():
            raise RuntimeError("Notion is not configured")

        headers = {
            "Authorization": f"Bearer {self._secret}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }

        title_text = payload.get("title") or "Brief"

        def build_properties(prefer_types: bool) -> dict[str, Any]:
            # prefer_types=False forces rich_text fallbacks where possible
            props: dict[str, Any] = {
                "Title": {"title": [{"text": {"content": title_text}}]},
                # legacy
                "language": {"rich_text": [{"text": {"content": str(payload.get("language", ""))}}]},
                "timestamp": {"rich_text": [{"text": {"content": str(payload.get("timestamp", ""))}}]},
                "caption": {"rich_text": [{"text": {"content": str(payload.get("caption", ""))}}]},
                "file_id": {"rich_text": [{"text": {"content": str(payload.get("file_id", ""))}}]},
                "file_name": {"rich_text": [{"text": {"content": str(payload.get("file_name", ""))}}]},
                "file_size": ({"number": payload.get("file_size")} if prefer_types else {"number": payload.get("file_size") if isinstance(payload.get("file_size"), (int, float)) else None}),
                "tg_username": {"rich_text": [{"text": {"content": str(payload.get("tg_username", ""))}}]},
                "tg_user_id": ({"number": int(payload.get("tg_user_id", 0))} if prefer_types else {"number": int(payload.get("tg_user_id", 0)) if str(payload.get("tg_user_id", "")).isdigit() else None}),
                "file_url": ({"url": str(payload.get("file_url", ""))} if (prefer_types and payload.get("file_url")) else ({"url": str(payload.get("file_url", ""))} if payload.get("file_url") else {"url": None})),
            }
            # extended metadata
            if prefer_types:
                props.update({
                    "Sender ID": {"number": int(payload.get("sender_id", 0)) if str(payload.get("sender_id", "")).isdigit() else None},
                    "Username": {"rich_text": [{"text": {"content": str(payload.get("username", ""))}}]},
                    "Full Name": {"rich_text": [{"text": {"content": str(payload.get("full_name", ""))}}]},
                    "Language": {"rich_text": [{"text": {"content": str(payload.get("language_code", ""))}}]},
                    "Sent At": {"date": {"start": str(payload.get("sent_at", ""))} if payload.get("sent_at") else None},
                    "Source Chat ID": {"number": int(payload.get("source_chat_id", 0)) if str(payload.get("source_chat_id", "")).isdigit() else None},
                    "Source Message ID": {"number": int(payload.get("source_message_id", 0)) if str(payload.get("source_message_id", "")).isdigit() else None},
                    "MIME": {"rich_text": [{"text": {"content": str(payload.get("mime_type", ""))}}]},
                    "file_unique_id": {"rich_text": [{"text": {"content": str(payload.get("file_unique_id", ""))}}]},
                    "Photo Width": {"number": payload.get("photo_width") if isinstance(payload.get("photo_width"), (int, float)) else None},
                    "Photo Height": {"number": payload.get("photo_height") if isinstance(payload.get("photo_height"), (int, float)) else None},
                })
            else:
                props.update({
                    "Sender ID": {"rich_text": [{"text": {"content": str(payload.get("sender_id", ""))}}]},
                    "Username": {"rich_text": [{"text": {"content": str(payload.get("username", ""))}}]},
                    "Full Name": {"rich_text": [{"text": {"content": str(payload.get("full_name", ""))}}]},
                    "Language": {"rich_text": [{"text": {"content": str(payload.get("language_code", ""))}}]},
                    "Sent At": {"rich_text": [{"text": {"content": str(payload.get("sent_at", ""))}}]},
                    "Source Chat ID": {"rich_text": [{"text": {"content": str(payload.get("source_chat_id", ""))}}]},
                    "Source Message ID": {"rich_text": [{"text": {"content": str(payload.get("source_message_id", ""))}}]},
                    "MIME": {"rich_text": [{"text": {"content": str(payload.get("mime_type", ""))}}]},
                    "file_unique_id": {"rich_text": [{"text": {"content": str(payload.get("file_unique_id", ""))}}]},
                    "Photo Width": {"rich_text": [{"text": {"content": str(payload.get("photo_width", ""))}}]},
                    "Photo Height": {"rich_text": [{"text": {"content": str(payload.get("photo_height", ""))}}]},
                })
            return props

        body = {
            "parent": {"database_id": self._db},
            "properties": build_properties(prefer_types=True),
        }

        timeout = httpx.Timeout(10.0, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post("https://api.notion.com/v1/pages", headers=headers, json=body)
            if 200 <= resp.status_code < 300:
                try:
                    data = resp.json()
                    return data.get("id")
                except Exception:
                    return None
            # Retry once with rich_text fallbacks if property schema mismatches
            fallback_body = {
                "parent": {"database_id": self._db},
                "properties": build_properties(prefer_types=False),
            }
            resp2 = await client.post("https://api.notion.com/v1/pages", headers=headers, json=fallback_body)
            try:
                resp2.raise_for_status()
                try:
                    data2 = resp2.json()
                    return data2.get("id")
                except Exception:
                    return None
            except Exception as e:
                logger.error(f"Failed to create Notion page: status={resp2.status_code} body={resp2.text[:500]}")
                raise e


