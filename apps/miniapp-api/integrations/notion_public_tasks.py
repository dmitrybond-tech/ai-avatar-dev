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
PROP_DESCRIPTION = "Description"


def _client() -> Client:
    if not NOTION_API_KEY:
        raise ValueError("NOTION_API_KEY is not set")
    return Client(auth=NOTION_API_KEY, timeout_ms=NOTION_TIMEOUT * 1000)


class PublicTaskOut(BaseModel):
    id: str
    title: str
    status: str
    scope: Optional[int] = None
    done: Optional[int] = None
    progressPct: int = Field(ge=0, le=100)
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    reviewAt: Optional[str] = None
    lastUpdated: str
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


def compute_progress(scope: Optional[int], done: Optional[int], fallback_pct: Optional[int] = None) -> int:
    """Compute progress percentage from scope/done, with fallback to Progress % property."""
    if scope is not None and done is not None:
        s = max(int(scope or 0), 0)
        d = max(int(done or 0), 0)
        if s > 0:
            return min(100, round(100 * d / s))
    if fallback_pct is not None:
        return max(0, min(100, int(fallback_pct)))
    return 0


def get_status_property(props: dict) -> Optional[str]:
    """Return status property type: 'status', 'select', or None."""
    prop = props.get(PROP_STATUS)
    if not prop:
        return None
    prop_type = prop.get("type")
    if prop_type in ("status", "select"):
        return prop_type
    return None


def set_status_property(status_name: Optional[str], is_status_type: bool) -> dict:
    if status_name is None:
        return {}
    return {PROP_STATUS: {"status": {"name": status_name}}} if is_status_type 
           else {PROP_STATUS: {"select": {"name": status_name}}}


def page_url(page_id: str) -> str:
    """Generate Notion page URL from page_id."""
    if not page_id:
        return ""
    return f"https://notion.so/{page_id.replace('-', '')}"


def extract_description(page_id: str, client: Client) -> Optional[str]:
    """
    Extract description from Notion page.
    First tries Description property (rich_text), then fetches blocks.
    Returns first 240 chars of plain text, stripped of newlines/markdown.
    """
    try:
        # First, try Description property if it exists
        page = client.pages.retrieve(page_id=page_id)
        props = page.get("properties", {})
        desc_prop = props.get(PROP_DESCRIPTION)
        if desc_prop and desc_prop.get("type") == "rich_text":
            rich_text = desc_prop.get("rich_text", [])
            if rich_text:
                text_parts = []
                for rt in rich_text:
                    plain = rt.get("plain_text", "")
                    if plain:
                        text_parts.append(plain)
                if text_parts:
                    desc = " ".join(text_parts)
                    # Strip newlines and limit to 240 chars
                    desc = desc.replace("\n", " ").replace("\r", " ").strip()
                    return desc[:240] if desc else None
        
        # Fallback: fetch blocks and extract from first paragraph/list
        blocks = client.blocks.children.list(block_id=page_id, page_size=30)
        for block in blocks.get("results", []):
            block_type = block.get("type")
            if block_type == "paragraph":
                rich_text = block.get("paragraph", {}).get("rich_text", [])
                text_parts = [rt.get("plain_text", "") for rt in rich_text if rt.get("plain_text")]
                if text_parts:
                    desc = " ".join(text_parts)
                    desc = desc.replace("\n", " ").replace("\r", " ").strip()
                    if desc:
                        return desc[:240]
            elif block_type == "bulleted_list_item":
                rich_text = block.get("bulleted_list_item", {}).get("rich_text", [])
                text_parts = [rt.get("plain_text", "") for rt in rich_text if rt.get("plain_text")]
                if text_parts:
                    desc = " ".join(text_parts)
                    desc = desc.replace("\n", " ").replace("\r", " ").strip()
                    if desc:
                        return desc[:240]
    except Exception:
        # Fail silently if description extraction fails
        pass
    return None


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


def _page_to_out(page: dict, is_status_type: bool, client: Optional[Client] = None) -> PublicTaskOut:
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
    progress_pct_prop = props.get(PROP_PROGRESS_PCT, {}).get("number")
    review_at = (props.get(PROP_REVIEW_AT, {}).get("date") or {}).get("start")
    tags = [x.get("name") for x in (props.get(PROP_TAGS, {}).get("multi_select") or []) if x.get("name")]
    page_id = page.get("id", "")
    
    # Extract description if client provided
    description = None
    if client:
        description = extract_description(page_id, client)
    
    return PublicTaskOut(
        id=page_id,
        title=title,
        status=status or "Backlog",
        scope=scope,
        done=done,
        progressPct=compute_progress(scope, done, fallback_pct=progress_pct_prop),
        description=description,
        reviewAt=review_at,
        lastUpdated=page.get("last_edited_time", ""),
        tags=tags,
        url=page_url(page_id),
    )


def _load_db_status_type(c: Client) -> bool:
    """Determine if Status property is 'status' type (True) or 'select' type (False)."""
    db = c.databases.retrieve(database_id=NOTION_PUBLIC_TASKS_DB_ID)
    status_type = get_status_property(db.get("properties", {}))
    return status_type == "status"


def _get_status_mapping(c: Client) -> Tuple[bool, dict]:
    """
    Retrieve database and build case-insensitive status mapping.
    Returns (is_status_type, mapping_dict) where mapping_dict maps normalized status names to actual DB values.
    """
    db = c.databases.retrieve(database_id=NOTION_PUBLIC_TASKS_DB_ID)
    props = db.get("properties", {})
    status_prop = props.get(PROP_STATUS, {})
    prop_type = status_prop.get("type")
    is_status_type = prop_type == "status"
    
    # Build mapping: normalized (lowercase, trimmed) -> actual status name
    status_mapping = {}
    if is_status_type:
        options = status_prop.get("status", {}).get("options", [])
        for opt in options:
            actual_name = opt.get("name", "").strip()
            if actual_name:
                normalized = actual_name.strip().lower()
                status_mapping[normalized] = actual_name
    else:
        options = status_prop.get("select", {}).get("options", [])
        for opt in options:
            actual_name = opt.get("name", "").strip()
            if actual_name:
                normalized = actual_name.strip().lower()
                status_mapping[normalized] = actual_name
    
    return is_status_type, status_mapping


def query_public_tasks(limit: int = 50, statuses: Optional[List[str]] = None, open_only: bool = True) -> List[PublicTaskOut]:
    """
    Query public tasks from Notion.
    
    Args:
        limit: Maximum number of tasks to return
        statuses: List of status names to filter by (case-insensitive). If None and open_only=True,
                  defaults to ["In Progress", "Review"]
        open_only: If True, exclude Done/Closed and items with progressPct >= 100
    
    Returns:
        List of PublicTaskOut objects
    
    Raises:
        ValueError: If NOTION_API_KEY or NOTION_PUBLIC_TASKS_DB_ID are missing
        Exception: On Notion API errors
    """
    if not NOTION_PUBLIC_TASKS_DB_ID:
        raise ValueError("NOTION_PUBLIC_TASKS_DB_ID is not configured")
    
    if not NOTION_API_KEY:
        raise ValueError("NOTION_API_KEY is not configured")
    
    try:
        c = _client()
    except ValueError as e:
        raise ValueError(f"Failed to initialize Notion client: {e}")
    
    try:
        is_status_type, status_mapping = _get_status_mapping(c)
    except APIResponseError as e:
        raise Exception(f"Notion query failed: {e}")
    except Exception as e:
        raise Exception(f"Failed to retrieve database schema: {e}")
    
    # Build filter: always require Public? = true
    filters = [{"property": PROP_PUBLIC, "checkbox": {"equals": True}}]
    
    # Normalize and map statuses to actual DB values
    statuses_to_query: List[str] = []
    if statuses:
        # Normalize input statuses and map to actual DB values
        for s in statuses:
            normalized = s.strip().lower()
            if normalized and normalized in status_mapping:
                statuses_to_query.append(status_mapping[normalized])
    elif open_only:
        # Default to ["In Progress", "Review"] when open_only=True and no statuses specified
        default_normalized = ["in progress", "review"]
        for norm in default_normalized:
            if norm in status_mapping:
                statuses_to_query.append(status_mapping[norm])
    
    # Add status filter if we have statuses to query
    if statuses_to_query:
        if is_status_type:
            status_conditions = [
                {"property": PROP_STATUS, "status": {"equals": s}}
                for s in statuses_to_query
            ]
        else:
            status_conditions = [
                {"property": PROP_STATUS, "select": {"equals": s}}
                for s in statuses_to_query
            ]
        if len(status_conditions) == 1:
            filters.append(status_conditions[0])
        else:
            filters.append({"or": status_conditions})
    
    # Combine filters with AND
    query_filter = {"and": filters} if len(filters) > 1 else filters[0]
    
    results: List[dict] = []
    has_more, cursor = True, None
    try:
        # Try to get database to check if PROP_LAST_UPDATED exists and is sortable
        db = c.databases.retrieve(database_id=NOTION_PUBLIC_TASKS_DB_ID)
        props = db.get("properties", {})
        has_last_updated = PROP_LAST_UPDATED in props
        
        while has_more and len(results) < limit:
            query_params = {
                "database_id": NOTION_PUBLIC_TASKS_DB_ID,
                "filter": query_filter,
                "page_size": min(limit - len(results), 100),
            }
            # Only add sort if property exists
            if has_last_updated:
                query_params["sorts"] = [
                    {"property": PROP_LAST_UPDATED, "direction": "descending"},
                ]
            if cursor:
                query_params["start_cursor"] = cursor
            
            resp = c.databases.query(**query_params)
            results.extend(resp.get("results", []))
            has_more = resp.get("has_more", False)
            cursor = resp.get("next_cursor")
        
        # Sort by last_edited_time if PROP_LAST_UPDATED wasn't available
        if not has_last_updated:
            results.sort(key=lambda p: p.get("last_edited_time", ""), reverse=True)
    except APIResponseError as e:
        raise Exception(f"Notion query failed: {e}")
    except Exception as e:
        raise Exception(f"Failed to query Notion database: {e}")
    
    # Convert pages to PublicTaskOut, extracting descriptions
    tasks = []
    for p in results[:limit]:
        try:
            tasks.append(_page_to_out(p, is_status_type, client=c))
        except Exception as e:
            # Log but continue processing other tasks
            import logging
            logging.warning(f"Failed to convert page {p.get('id', 'unknown')}: {e}")
            continue
    
    # Apply additional client-side filtering for open_only
    if open_only:
        tasks = [
            t for t in tasks
            if t.status not in {"Done", "Closed"} and t.progressPct < 100
        ]
    
    # Final case-insensitive status filtering if statuses were provided (double-check)
    if statuses:
        statuses_normalized = [s.strip().lower() for s in statuses if s.strip()]
        tasks = [t for t in tasks if t.status.strip().lower() in statuses_normalized]
    
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
    return _page_to_out(page, is_status_type, client=c)


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
        return _page_to_out(page, is_status_type, client=c)
    page = c.pages.update(page_id, properties=props)
    return _page_to_out(page, is_status_type, client=c)


def add_comment(page_id: str, text: str) -> None:
    c = _client()
    t = (text or "")[:1000]
    c.comments.create(parent={"page_id": page_id}, rich_text=[{"text": {"content": t}}])


