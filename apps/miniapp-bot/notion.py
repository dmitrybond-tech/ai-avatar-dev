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

    async def create_brief_page(self, payload: dict[str, Any]) -> None:
        if not self.configured():
            raise RuntimeError("Notion is not configured")

        headers = {
            "Authorization": f"Bearer {self._secret}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }

        title_text = payload.get("title") or "Brief"
        properties: dict[str, Any] = {
            "Title": {"title": [{"text": {"content": title_text}}]},
            "language": {"rich_text": [{"text": {"content": str(payload.get("language", ""))}}]},
            "timestamp": {"rich_text": [{"text": {"content": str(payload.get("timestamp", ""))}}]},
            "caption": {"rich_text": [{"text": {"content": str(payload.get("caption", ""))}}]},
            "file_id": {"rich_text": [{"text": {"content": str(payload.get("file_id", ""))}}]},
            "file_name": {"rich_text": [{"text": {"content": str(payload.get("file_name", ""))}}]},
            "file_size": {"number": payload.get("file_size") if isinstance(payload.get("file_size"), (int, float)) else None},
            "tg_username": {"rich_text": [{"text": {"content": str(payload.get("tg_username", ""))}}]},
            "tg_user_id": {"number": int(payload.get("tg_user_id", 0)) if str(payload.get("tg_user_id", "")).isdigit() else None},
            "file_url": {"url": str(payload.get("file_url", ""))} if payload.get("file_url") else {"url": None},
        }

        body = {
            "parent": {"database_id": self._db},
            "properties": properties,
        }

        timeout = httpx.Timeout(10.0, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post("https://api.notion.com/v1/pages", headers=headers, json=body)
            try:
                resp.raise_for_status()
            except Exception as e:
                logger.error(f"Failed to create Notion page: status={resp.status_code} body={resp.text[:500]}")
                raise e


