import os
from datetime import datetime
from typing import List, Optional

from notion_client import Client
from pydantic import BaseModel, Field


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name, default)
    return value if value not in (None, "") else default


class PublicTaskOut(BaseModel):
    id: str
    title: str
    status: Optional[str] = None
    progressPct: int = Field(default=0)
    reviewAt: Optional[str] = None
    lastUpdated: str
    tags: List[str] = Field(default_factory=list)
    url: Optional[str] = None


def _get_title(properties: dict) -> str:
    # Try to locate the title property robustly
    for prop_name, prop in properties.items():
        if prop.get("type") == "title":
            title_items = prop.get("title") or []
            if title_items:
                texts = [t.get("plain_text", "") for t in title_items]
                joined = "".join(texts).strip()
                if joined:
                    return joined
    # Fallbacks by common names
    for key in ("Name", "Title"):
        prop = properties.get(key)
        if prop and prop.get("type") == "title":
            items = prop.get("title") or []
            if items:
                return "".join([t.get("plain_text", "") for t in items]).strip()
    return ""


def _get_status(properties: dict) -> Optional[str]:
    prop = properties.get("Status")
    if not prop:
        return None
    if prop.get("type") == "status":
        val = prop.get("status") or {}
        return val.get("name")
    if prop.get("type") == "select":
        val = prop.get("select") or {}
        return val.get("name")
    return None


def _get_progress_pct(properties: dict) -> int:
    prop = properties.get("Progress %")
    if prop and prop.get("type") == "number":
        num = prop.get("number")
        try:
            return int(num or 0)
        except Exception:
            return 0
    return 0


def _get_review_at(properties: dict) -> Optional[str]:
    prop = properties.get("Review At")
    if prop and prop.get("type") == "date":
        date_val = prop.get("date") or {}
        start = date_val.get("start")
        if start:
            # Ensure ISO 8601 date string
            return start
    return None


def _get_tags(properties: dict) -> List[str]:
    prop = properties.get("Tags")
    if prop and prop.get("type") == "multi_select":
        items = prop.get("multi_select") or []
        return [i.get("name") for i in items if i.get("name")]
    return []


def _iso(dt: str | datetime) -> str:
    if isinstance(dt, str):
        return dt
    return dt.isoformat()


def _init_client() -> Client:
    api_key = _env("NOTION_API_KEY")
    if not api_key:
        raise RuntimeError("NOTION_API_KEY is not set")
    timeout_val = int(_env("NOTION_TIMEOUT", "10") or "10")
    return Client(auth=api_key, timeout=timeout_val)


def query_public_tasks(limit: int = 100) -> List[PublicTaskOut]:
    db_id = _env("NOTION_PUBLIC_TASKS_DB_ID")
    if not db_id:
        raise RuntimeError("NOTION_PUBLIC_TASKS_DB_ID is not set")

    client = _init_client()
    page_size = max(1, min(limit, 100))

    resp = client.databases.query(
        **{
            "database_id": db_id,
            "filter": {
                "property": "Public?",
                "checkbox": {"equals": True},
            },
            "page_size": page_size,
        }
    )

    results = []
    for row in resp.get("results", []):
        props = row.get("properties", {})
        task = PublicTaskOut(
            id=row.get("id", ""),
            title=_get_title(props),
            status=_get_status(props),
            progressPct=_get_progress_pct(props),
            reviewAt=_get_review_at(props),
            lastUpdated=_iso(row.get("last_edited_time", "")),
            tags=_get_tags(props),
            url=row.get("url"),
        )
        results.append(task)

    return results


