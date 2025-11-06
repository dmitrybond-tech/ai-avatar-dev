from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Tuple

from notion_client import Client, APIResponseError
from pydantic import BaseModel, Field

import os


# Environment
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "").strip()
NOTION_PUBLIC_TASKS_DB_ID = os.getenv("NOTION_PUBLIC_TASKS_DB_ID", "").strip()
NOTION_TIMEOUT = int(os.getenv("NOTION_TIMEOUT", "10"))


# Notion properties (must match DB)
PROP_TITLE = "Name"
PROP_STATUS = "Status"
PROP_PUBLIC = "Public?"
PROP_SCOPE = "Scope"
PROP_DONE = "Done"
PROP_PROGRESS_PCT = "Progress %"
PROP_REVIEW_AT = "Review At"
PROP_LAST_UPDATED = "Last Updated"
PROP_TAGS = "Tags"
PROP_SOURCE = "Source"


def _client() -> Client:
    if not NOTION_API_KEY:
        raise ValueError("NOTION_API_KEY is not set")
    return Client(auth=NOTION_API_KEY, timeout_ms=NOTION_TIMEOUT * 1000)


class PublicTaskOut(BaseModel):
    id: str
    title: str
    status: str
    progressPct: int = Field(ge=0, le=100)
    reviewAt: Optional[str] = None
    lastUpdated: str
    tags: List[str] = Field(default_factory=list)
    url: str


class PublicTaskCreate(BaseModel):
    title: str
    status: Optional[str] = None
    scope: Optional[int] = None
    done: Optional[int] = None
    review_at: Optional[str] = None
    tags: Optional[List[str]] = None
    source: Optional[str] = None


class PublicTaskUpdate(BaseModel):
    status: Optional[str] = None
    scope: Optional[int] = None
    done: Optional[int] = None
    review_at: Optional[str] = None
    tags: Optional[List[str]] = None


def compute_progress(scope: Optional[int], done: Optional[int]) -> int:
    s = max(int(scope or 0), 0)
    d = max(int(done or 0), 0)
    return 0 if s == 0 else min(100, round(100 * d / s))


def _status_property_name_and_type(db_props: dict) -> Tuple[bool, str]:
    # Return (is_status_type, property_type_str)
    prop = db_props.get(PROP_STATUS)
    if not prop:
        return True, "status"  # default
    t = prop.get("type")
    return (t == "status", t or "status")


def set_status_property(status_name: Optional[str], is_status_type: bool) -> dict:
    if status_name is None:
        return {}
    return {PROP_STATUS: {"status": {"name": status_name}}} if is_status_type 
           else {PROP_STATUS: {"select": {"name": status_name}}}


def assert_schema() -> None:
    """Verify Notion database schema matches expected fields. Logs warnings instead of crashing."""
    if not NOTION_PUBLIC_TASKS_DB_ID:
        return
    try:
        c = _client()
        db = c.databases.retrieve(database_id=NOTION_PUBLIC_TASKS_DB_ID)
        props = db.get("properties", {})
        required = {
            PROP_TITLE: "title",
            PROP_STATUS: ("status", "select"),
            PROP_PUBLIC: "checkbox",
            PROP_SCOPE: "number",
            PROP_DONE: "number",
            PROP_PROGRESS_PCT: "number",
            PROP_REVIEW_AT: "date",
        }
        missing, wrong = [], []
        for k, exp in required.items():
            if k not in props:
                missing.append(k)
                continue
            actual = props[k].get("type")
            if isinstance(exp, tuple):
                if actual not in exp:
                    wrong.append(f"{k} (got {actual})")
            elif actual != exp:
                wrong.append(f"{k} (got {actual})")
        if missing or wrong:
            # Log warning instead of crashing
            import warnings
            warnings.warn(
                f"Notion schema mismatch: missing={missing}, wrong={wrong}. "
                "Tasks API may not work correctly.",
                UserWarning
            )
    except Exception as e:
        # Log and continue if schema check fails
        import warnings
        warnings.warn(f"Notion schema check failed: {e}", UserWarning)


def _page_to_out(page: dict, is_status_type: bool) -> PublicTaskOut:
    props = page.get("properties", {})
    title_arr = props.get(PROP_TITLE, {}).get("title", [])
    title = "".join(rt.get("plain_text", "") for rt in title_arr)
    status_prop = props.get(PROP_STATUS, {})
    if is_status_type:
        status = (status_prop.get("status") or {}).get("name") or "Backlog"
    else:
        status = (status_prop.get("select") or {}).get("name") or "Backlog"
    scope = props.get(PROP_SCOPE, {}).get("number")
    done = props.get(PROP_DONE, {}).get("number")
    review_at = (props.get(PROP_REVIEW_AT, {}).get("date") or {}).get("start")
    tags = [x.get("name") for x in (props.get(PROP_TAGS, {}).get("multi_select") or []) if x.get("name")]
    page_id = page.get("id", "")
    return PublicTaskOut(
        id=page_id,
        title=title,
        status=status or "Backlog",
        progressPct=compute_progress(scope, done),
        reviewAt=review_at,
        lastUpdated=page.get("last_edited_time", ""),
        tags=tags,
        url=f"https://notion.so/{page_id.replace('-', '')}" if page_id else "",
    )


def _load_db_status_type(c: Client) -> bool:
    db = c.databases.retrieve(database_id=NOTION_PUBLIC_TASKS_DB_ID)
    is_status_type, _ = _status_property_name_and_type(db.get("properties", {}))
    return is_status_type


def query_public_tasks(limit: int = 100, open_only: bool = True) -> List[PublicTaskOut]:
    if not NOTION_PUBLIC_TASKS_DB_ID:
        return []
    c = _client()
    is_status_type = _load_db_status_type(c)
    results: List[dict] = []
    has_more, cursor = True, None
    while has_more and len(results) < limit:
        resp = c.databases.query(
            database_id=NOTION_PUBLIC_TASKS_DB_ID,
            filter={"property": PROP_PUBLIC, "checkbox": {"equals": True}},
            sorts=[
                {"property": PROP_LAST_UPDATED, "direction": "descending"},
                {"property": PROP_REVIEW_AT, "direction": "ascending"},
            ],
            page_size=min(limit, 100),
            start_cursor=cursor,
        ) if cursor else c.databases.query(
            database_id=NOTION_PUBLIC_TASKS_DB_ID,
            filter={"property": PROP_PUBLIC, "checkbox": {"equals": True}},
            sorts=[
                {"property": PROP_LAST_UPDATED, "direction": "descending"},
                {"property": PROP_REVIEW_AT, "direction": "ascending"},
            ],
            page_size=min(limit, 100),
        )
        results.extend(resp.get("results", []))
        has_more = resp.get("has_more", False)
        cursor = resp.get("next_cursor")
    tasks = [_page_to_out(p, is_status_type) for p in results[:limit]]
    
    # Filter out completed tasks if open_only is True
    if open_only:
        tasks = [
            t for t in tasks
            if t.status not in {"Done", "Closed"} and t.progressPct < 100
        ]
    
    return tasks


def create_task(data: PublicTaskCreate) -> PublicTaskOut:
    if not NOTION_PUBLIC_TASKS_DB_ID:
        raise ValueError("NOTION_PUBLIC_TASKS_DB_ID is not set")
    c = _client()
    is_status_type = _load_db_status_type(c)
    status = data.status or "Backlog"
    scope = data.scope or 0
    done = data.done or 0
    src = data.source or "MiniApp"
    props = {
        PROP_TITLE: {"title": [{"text": {"content": data.title}}]},
        PROP_PUBLIC: {"checkbox": True},
        PROP_SCOPE: {"number": scope},
        PROP_DONE: {"number": done},
        PROP_PROGRESS_PCT: {"number": compute_progress(scope, done)},
        PROP_SOURCE: {"select": {"name": src}},
        **set_status_property(status, is_status_type),
    }
    if data.review_at:
        props[PROP_REVIEW_AT] = {"date": {"start": data.review_at}}
    if data.tags:
        props[PROP_TAGS] = {"multi_select": [{"name": t} for t in data.tags]}
    page = c.pages.create(parent={"database_id": NOTION_PUBLIC_TASKS_DB_ID}, properties=props)
    return _page_to_out(page, is_status_type)


def update_task(page_id: str, data: PublicTaskUpdate) -> PublicTaskOut:
    c = _client()
    is_status_type = _load_db_status_type(c)
    props: dict = {}
    if data.status is not None:
        props.update(set_status_property(data.status, is_status_type))
    need_progress = (data.scope is not None) or (data.done is not None)
    if need_progress:
        page = c.pages.retrieve(page_id)
        p = page.get("properties", {})
        cur_scope = p.get(PROP_SCOPE, {}).get("number") or 0
        cur_done = p.get(PROP_DONE, {}).get("number") or 0
        new_scope = data.scope if data.scope is not None else cur_scope
        new_done = data.done if data.done is not None else cur_done
        props[PROP_SCOPE] = {"number": new_scope}
        props[PROP_DONE] = {"number": new_done}
        props[PROP_PROGRESS_PCT] = {"number": compute_progress(new_scope, new_done)}
    if data.review_at is not None:
        props[PROP_REVIEW_AT] = {"date": {"start": data.review_at}}
    if data.tags is not None:
        props[PROP_TAGS] = {"multi_select": [{"name": t} for t in data.tags]}
    if not props:
        page = c.pages.retrieve(page_id)
        return _page_to_out(page, is_status_type)
    page = c.pages.update(page_id, properties=props)
    return _page_to_out(page, is_status_type)


def add_comment(page_id: str, text: str) -> None:
    c = _client()
    t = (text or "")[:1000]
    c.comments.create(parent={"page_id": page_id}, rich_text=[{"text": {"content": t}}])


