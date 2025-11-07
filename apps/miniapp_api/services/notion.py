"""Notion helpers for brief uploads."""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from notion_client import APIResponseError, Client


logger = logging.getLogger(__name__)


async def create_brief_page(
    notion_token: str,
    db_id: str,
    data: dict,
) -> Optional[str]:
    """Create a Notion page for the uploaded brief."""
    if not notion_token or not db_id:
        logger.warning("Notion credentials missing; skipping page creation")
        return None

    def _create_page() -> Optional[str]:
        try:
            client = Client(auth=notion_token)
            properties = {
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": f"Brief | {data.get('company', 'Unknown')} | {data.get('name', 'Unknown')}"
                            }
                        }
                    ]
                },
                "Status": {
                    "status": {"name": "Backlog"}
                },
                "Request ID": {
                    "rich_text": [
                        {"text": {"content": data.get("request_id", "")}}
                    ]
                },
                "Email": {"email": data.get("email", "")},
                "Phone": {"phone_number": data.get("phone", "")},
                "Locale": {
                    "select": {"name": (data.get("locale", "en") or "en").upper()}
                },
                "Source": {"select": {"name": "Miniapp Brief"}},
                "Comment": {
                    "rich_text": [
                        {
                            "text": {
                                "content": data.get("message", "") or ""
                            }
                        }
                    ]
                },
            }

            page = client.pages.create(
                parent={"database_id": db_id},
                properties=properties,
            )
            return page.get("id")
        except APIResponseError as exc:
            logger.error(
                "Notion API error (request_id=%s, code=%s)",
                exc.request_id,
                exc.code,
            )
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("Notion page creation failed: %s", exc, exc_info=True)
            raise

    try:
        page_id = await asyncio.to_thread(_create_page)
        logger.info("Notion page created for brief request")
        return page_id
    except Exception:
        return None


