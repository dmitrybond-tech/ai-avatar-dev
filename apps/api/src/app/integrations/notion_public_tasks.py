"""Notion integration for Public On-Board Tasks."""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from threading import Lock
from typing import Dict, List, Optional

from httpx import RequestError
from notion_client import APIResponseError, Client
from pydantic import BaseModel, Field, field_validator

from app.core.settings import settings
from app.core.logging import get_logger
from app.integrations.notion_client import (
    clear_client_cache as clear_shared_notion_cache,
    get_notion_client as build_notion_client,
)

logger = get_logger(__name__)

DEFAULT_LOCALE_KEY = "default"

# Mapping constants
STATUS_MAP = {"Backlog", "In Progress", "Review", "Blocked", "Done"}
SOURCE_VALUES = {"MiniApp", "Bot", "Manual"}

# Property names (must match Notion DB)
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

# Initialize Notion client + cache state
_notion_client: Optional[Client] = None
_notion_client_lock = Lock()
_tasks_cache: Dict[str, "_TasksCacheEntry"] = {}
_tasks_cache_lock = Lock()


def get_notion_client() -> Client:
    """Get or create Notion client instance."""
    global _notion_client
    if _notion_client is not None:
        return _notion_client

    with _notion_client_lock:
        if _notion_client is not None:
            return _notion_client

        api_key = (settings.notion_api_key or "").strip()
        if not api_key:
            raise ValueError("NOTION_API_KEY is not set")

        timeout = getattr(settings, "notion_timeout", None)
        try:
            client = build_notion_client(api_key, timeout)
        except Exception as exc:
            logger.error("Failed to initialize Notion client: %s", exc, exc_info=True)
            raise

        _notion_client = client
        return client


def compute_progress(scope: int, done: int) -> int:
    """Compute progress percentage from scope and done values."""
    scope = max(int(scope or 0), 0)
    done = max(int(done or 0), 0)
    if scope == 0:
        return 0
    return min(100, round(100 * done / scope))


# Pydantic Models
class PublicTaskIn(BaseModel):
    """Input model for creating a task."""
    title: str = Field(..., min_length=1, max_length=200)
    status: Optional[str] = Field(None, max_length=50)
    scope: Optional[int] = Field(None, ge=0)
    done: Optional[int] = Field(None, ge=0)
    review_at: Optional[datetime] = None
    tags: Optional[List[str]] = Field(None, max_length=10)
    source: Optional[str] = Field("MiniApp", max_length=20)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in STATUS_MAP:
            raise ValueError(f"Status must be one of: {', '.join(STATUS_MAP)}")
        return v

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in SOURCE_VALUES:
            raise ValueError(f"Source must be one of: {', '.join(SOURCE_VALUES)}")
        return v


class PublicTaskUpdate(BaseModel):
    """Update model for partial task updates."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    status: Optional[str] = Field(None, max_length=50)
    scope: Optional[int] = Field(None, ge=0)
    done: Optional[int] = Field(None, ge=0)
    review_at: Optional[datetime] = None
    tags: Optional[List[str]] = Field(None, max_length=10)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in STATUS_MAP:
            raise ValueError(f"Status must be one of: {', '.join(STATUS_MAP)}")
        return v


class PublicTaskOut(BaseModel):
    """Output model for public task listing."""
    id: str
    title: str
    status: str
    progress_pct: int = Field(..., ge=0, le=100)
    review_at: Optional[str] = None
    last_updated: str
    tags: List[str] = Field(default_factory=list)
    url: str


@dataclass(slots=True)
class _TasksCacheEntry:
    items: List[PublicTaskOut]
    fetched_at: datetime
    expires_at: datetime
    fetched_limit: int


def _cache_ttl_seconds() -> int:
    raw_value = getattr(settings, "notion_cache_ttl_tasks", 300)
    try:
        value = int(raw_value)
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return 300
    return max(value, 0)


def _normalize_locale(locale: Optional[str]) -> str:
    if not locale:
        return DEFAULT_LOCALE_KEY
    normalized = locale.strip().lower()
    if not normalized:
        return DEFAULT_LOCALE_KEY
    normalized = normalized.split(",", 1)[0]
    return (normalized.split("-", 1)[0] or DEFAULT_LOCALE_KEY).strip() or DEFAULT_LOCALE_KEY


def _get_cache_entry(locale: str) -> Optional[_TasksCacheEntry]:
    with _tasks_cache_lock:
        return _tasks_cache.get(locale)


def _save_cache_entry(locale: str, entry: _TasksCacheEntry) -> None:
    with _tasks_cache_lock:
        _tasks_cache[locale] = entry


def _cache_snapshot(locale: str) -> Dict[str, Optional[str]]:
    entry = _get_cache_entry(locale)
    if not entry:
        return {"count": 0, "last_updated": None}
    return {
        "count": len(entry.items),
        "last_updated": entry.fetched_at.isoformat(),
    }


def get_tasks_cache_snapshot(locale: Optional[str] = None) -> Dict[str, Optional[str]]:
    """Return cache statistics for debug endpoints."""
    return _cache_snapshot(_normalize_locale(locale))


def reset_tasks_cache() -> None:
    """Reset cached tasks and Notion client (testing only)."""
    global _notion_client
    with _tasks_cache_lock:
        _tasks_cache.clear()
    with _notion_client_lock:
        _notion_client = None
    clear_shared_notion_cache()


class PublicTaskCreate(BaseModel):
    """Model for creating a task (extends PublicTaskIn with defaults)."""
    title: str = Field(..., min_length=1, max_length=200)
    status: Optional[str] = None
    scope: Optional[int] = None
    done: Optional[int] = None
    review_at: Optional[datetime] = None
    tags: Optional[List[str]] = None
    source: Optional[str] = "MiniApp"

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in STATUS_MAP:
            raise ValueError(f"Status must be one of: {', '.join(STATUS_MAP)}")
        return v

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in SOURCE_VALUES:
            raise ValueError(f"Source must be one of: {', '.join(SOURCE_VALUES)}")
        return v


def _extract_title(prop: dict) -> str:
    """Extract title text from Notion property."""
    if prop.get("type") != "title":
        return ""
    title_array = prop.get("title", [])
    return "".join(rt.get("plain_text", "") for rt in title_array)


def _extract_status(prop: dict) -> str:
    """Extract status from Notion property."""
    if prop.get("type") != "select":
        return "Backlog"
    select = prop.get("select")
    return select.get("name", "Backlog") if select else "Backlog"


def _extract_number(prop: dict) -> Optional[int]:
    """Extract number from Notion property."""
    if prop.get("type") != "number":
        return None
    num = prop.get("number")
    return int(num) if num is not None else None


def _extract_date(prop: dict) -> Optional[str]:
    """Extract ISO date string from Notion property."""
    if prop.get("type") != "date":
        return None
    date_obj = prop.get("date")
    if not date_obj:
        return None
    start = date_obj.get("start")
    return start if start else None


def _extract_multi_select(prop: dict) -> List[str]:
    """Extract multi-select values from Notion property."""
    if prop.get("type") != "multi_select":
        return []
    multi_select = prop.get("multi_select", [])
    return [ms.get("name", "") for ms in multi_select if ms.get("name")]


def _extract_last_edited_time(page: dict) -> str:
    """Extract last edited time from page."""
    return page.get("last_edited_time", "")


def _build_notion_url(page_id: str) -> str:
    """Build public Notion page URL."""
    # Notion page URLs are in format: https://notion.so/{page_id_without_dashes}
    page_id_clean = page_id.replace("-", "")
    return f"https://notion.so/{page_id_clean}"


def _page_to_public_task_out(page: dict) -> PublicTaskOut:
    """Convert Notion page to PublicTaskOut."""
    props = page.get("properties", {})
    page_id = page.get("id", "")

    title = _extract_title(props.get(PROP_TITLE, {}))
    status = _extract_status(props.get(PROP_STATUS, {}))
    scope = _extract_number(props.get(PROP_SCOPE, {})) or 0
    done = _extract_number(props.get(PROP_DONE, {})) or 0
    progress_pct = compute_progress(scope, done)
    review_at = _extract_date(props.get(PROP_REVIEW_AT, {}))
    tags = _extract_multi_select(props.get(PROP_TAGS, {}))
    last_updated = _extract_last_edited_time(page)

    return PublicTaskOut(
        id=page_id,
        title=title,
        status=status,
        progress_pct=progress_pct,
        review_at=review_at,
        last_updated=last_updated,
        tags=tags,
        url=_build_notion_url(page_id),
    )


def _set_meta(meta: Optional[Dict[str, object]], **values: object) -> None:
    if meta is not None:
        meta.update(values)


def _should_retry(exc: Exception) -> bool:
    if isinstance(exc, APIResponseError):
        status = getattr(exc, "status", None) or getattr(exc, "status_code", None)
        if status is None:
            response = getattr(exc, "response", None)
            status = getattr(response, "status_code", None) if response else None
        if isinstance(status, int) and (status == 429 or 500 <= status < 600):
            return True
        code = (getattr(exc, "code", "") or "").lower()
        if code in {"rate_limited", "service_unavailable", "internal_server_error"}:
            return True
    if isinstance(exc, RequestError):
        return True
    return False


def _execute_query_with_retries(client: Client, query_params: Dict[str, object]) -> Dict[str, object]:
    attempts = 3
    for attempt in range(attempts):
        try:
            return client.databases.query(**query_params)
        except Exception as exc:
            should_retry = _should_retry(exc)
            if attempt == attempts - 1 or not should_retry:
                raise
            wait_seconds = min(4.0, 0.5 * (2 ** attempt))
            logger.warning(
                "Retrying Notion tasks query",
                extra={"attempt": attempt + 1, "delay": wait_seconds, "error": str(exc)},
            )
            time.sleep(wait_seconds)
    raise RuntimeError("Failed to query Notion tasks")  # pragma: no cover - defensive


def _fetch_public_tasks(client: Client, db_id: str, limit: int) -> List[PublicTaskOut]:
    results: List[dict] = []
    has_more = True
    start_cursor: Optional[str] = None

    while has_more and len(results) < limit:
        query_params: Dict[str, object] = {
            "database_id": db_id,
            "filter": {
                "property": PROP_PUBLIC,
                "checkbox": {"equals": True},
            },
            "sorts": [
                {"property": PROP_LAST_UPDATED, "direction": "descending"},
                {"property": PROP_REVIEW_AT, "direction": "ascending"},
            ],
            "page_size": min(limit, 100),
        }
        if start_cursor:
            query_params["start_cursor"] = start_cursor

        response = _execute_query_with_retries(client, query_params)
        pages = response.get("results", [])
        if isinstance(pages, list):
            results.extend(pages)

        has_more = bool(response.get("has_more", False))
        start_cursor = response.get("next_cursor")

    return [_page_to_public_task_out(page) for page in results[:limit]]


def query_public_tasks(
    limit: int = 100,
    *,
    locale: Optional[str] = None,
    meta: Optional[Dict[str, object]] = None,
) -> List[PublicTaskOut]:
    """Query public tasks from Notion database with caching and stale fallback."""
    resolved_locale = _normalize_locale(locale)
    db_id = (settings.notion_public_tasks_db_id or "").strip()
    if not db_id:
        raise ValueError("NOTION_PUBLIC_TASKS_DB_ID is not set")

    client = get_notion_client()
    ttl = _cache_ttl_seconds()
    now = datetime.now(timezone.utc)
    cache_entry = _get_cache_entry(resolved_locale)

    if cache_entry and cache_entry.expires_at > now and cache_entry.fetched_limit >= limit:
        _set_meta(
            meta,
            stale=False,
            source="cache",
            last_updated=cache_entry.fetched_at.isoformat(),
            count=len(cache_entry.items),
        )
        return cache_entry.items[:limit]

    stale_candidate = cache_entry if cache_entry and cache_entry.fetched_limit >= limit else None

    try:
        tasks = _fetch_public_tasks(client, db_id, limit)
    except Exception as exc:
        if stale_candidate and stale_candidate.items and _should_retry(exc):
            logger.warning(
                "Serving stale Notion tasks",
                extra={"locale": resolved_locale, "error": str(exc)},
            )
            _set_meta(
                meta,
                stale=True,
                source="cache",
                last_updated=stale_candidate.fetched_at.isoformat(),
                count=len(stale_candidate.items),
                error=str(exc),
            )
            return stale_candidate.items[:limit]
        if isinstance(exc, APIResponseError):
            logger.error(
                "Notion API error: %s - %s (request_id: %s)",
                exc.code,
                exc.message,
                getattr(exc, "request_id", None),
            )
            raise ValueError(f"Notion API error: {exc.message}") from exc
        logger.error("Error querying Notion tasks: %s", exc, exc_info=True)
        raise

    fetched_at = datetime.now(timezone.utc)
    expires_at = fetched_at + timedelta(seconds=ttl) if ttl else fetched_at
    new_entry = _TasksCacheEntry(
        items=tasks,
        fetched_at=fetched_at,
        expires_at=expires_at,
        fetched_limit=max(limit, len(tasks)),
    )
    _save_cache_entry(resolved_locale, new_entry)
    _set_meta(
        meta,
        stale=False,
        source="notion",
        last_updated=fetched_at.isoformat(),
        count=len(tasks),
    )
    return tasks[:limit]


def create_task(
    title: str,
    status: Optional[str] = None,
    scope: Optional[int] = None,
    done: Optional[int] = None,
    review_at: Optional[datetime] = None,
    tags: Optional[List[str]] = None,
    source: Optional[str] = "MiniApp",
) -> PublicTaskOut:
    """Create a new task in Notion."""
    client = get_notion_client()
    db_id = settings.notion_public_tasks_db_id

    if not db_id:
        raise ValueError("NOTION_PUBLIC_TASKS_DB_ID is not set")

    # Set defaults
    status = status or "Backlog"
    scope = scope or 0
    done = done or 0
    source = source or "MiniApp"
    progress_pct = compute_progress(scope, done)

    # Build properties
    properties = {
        PROP_TITLE: {"title": [{"text": {"content": title}}]},
        PROP_STATUS: {"status": {"name": status}},
        PROP_PUBLIC: {"checkbox": True},
        PROP_SCOPE: {"number": scope},
        PROP_DONE: {"number": done},
        PROP_PROGRESS_PCT: {"number": progress_pct},
        PROP_SOURCE: {"select": {"name": source}},
    }

    if review_at:
        properties[PROP_REVIEW_AT] = {"date": {"start": review_at.isoformat()}}

    if tags:
        properties[PROP_TAGS] = {"multi_select": [{"name": tag} for tag in tags]}

    try:
        page = client.pages.create(
            parent={"database_id": db_id},
            properties=properties,
        )
        return _page_to_public_task_out(page)

    except APIResponseError as e:
        logger.error(f"Notion API error creating task: {e.code} - {e.message} (request_id: {e.request_id})")
        raise ValueError(f"Notion API error: {e.message}") from e
    except Exception as e:
        logger.error(f"Error creating Notion task: {e}")
        raise


def update_task(
    notion_page_id: str,
    title: Optional[str] = None,
    status: Optional[str] = None,
    scope: Optional[int] = None,
    done: Optional[int] = None,
    review_at: Optional[datetime] = None,
    tags: Optional[List[str]] = None,
) -> PublicTaskOut:
    """Update a task in Notion."""
    client = get_notion_client()

    # Build properties to update
    properties = {}

    if title is not None:
        properties[PROP_TITLE] = {"title": [{"text": {"content": title}}]}

    if status is not None:
        properties[PROP_STATUS] = {"status": {"name": status}}

    if scope is not None or done is not None:
        # Need to fetch current values to compute progress
        try:
            page = client.pages.retrieve(notion_page_id)
            props = page.get("properties", {})
            current_scope = _extract_number(props.get(PROP_SCOPE, {})) or 0
            current_done = _extract_number(props.get(PROP_DONE, {})) or 0

            new_scope = scope if scope is not None else current_scope
            new_done = done if done is not None else current_done
            progress_pct = compute_progress(new_scope, new_done)

            properties[PROP_SCOPE] = {"number": new_scope}
            properties[PROP_DONE] = {"number": new_done}
            properties[PROP_PROGRESS_PCT] = {"number": progress_pct}
        except APIResponseError as e:
            logger.error(f"Notion API error fetching task: {e.code} - {e.message} (request_id: {e.request_id})")
            raise ValueError(f"Notion API error: {e.message}") from e

    if review_at is not None:
        properties[PROP_REVIEW_AT] = {"date": {"start": review_at.isoformat()}}

    if tags is not None:
        properties[PROP_TAGS] = {"multi_select": [{"name": tag} for tag in tags]}

    if not properties:
        # No updates, just fetch and return
        try:
            page = client.pages.retrieve(notion_page_id)
            return _page_to_public_task_out(page)
        except APIResponseError as e:
            logger.error(f"Notion API error fetching task: {e.code} - {e.message} (request_id: {e.request_id})")
            raise ValueError(f"Notion API error: {e.message}") from e

    try:
        page = client.pages.update(notion_page_id, properties=properties)
        return _page_to_public_task_out(page)

    except APIResponseError as e:
        logger.error(f"Notion API error updating task: {e.code} - {e.message} (request_id: {e.request_id})")
        raise ValueError(f"Notion API error: {e.message}") from e
    except Exception as e:
        logger.error(f"Error updating Notion task: {e}")
        raise


def add_comment(notion_page_id: str, text: str) -> None:
    """Add an internal comment to a Notion page."""
    client = get_notion_client()

    # Sanitize text length
    text = text[:1000] if len(text) > 1000 else text

    try:
        # Use the discussions.create endpoint to add a comment
        client.comments.create(
            parent={"page_id": notion_page_id},
            rich_text=[{"text": {"content": text}}],
        )
        logger.info(f"Added comment to page {notion_page_id}")

    except APIResponseError as e:
        logger.error(f"Notion API error adding comment: {e.code} - {e.message} (request_id: {e.request_id})")
        raise ValueError(f"Notion API error: {e.message}") from e
    except Exception as e:
        logger.error(f"Error adding comment to Notion page: {e}")
        raise


def assert_schema() -> None:
    """Assert that the Notion database has the required schema."""
    client = get_notion_client()
    db_id = settings.notion_public_tasks_db_id

    if not db_id:
        raise ValueError("NOTION_PUBLIC_TASKS_DB_ID is not set")

    try:
        db = client.databases.retrieve(database_id=db_id)
        properties = db.get("properties", {})

        required_props = {
            PROP_TITLE: "title",
            PROP_STATUS: "select",
            PROP_PUBLIC: "checkbox",
            PROP_SCOPE: "number",
            PROP_DONE: "number",
            PROP_PROGRESS_PCT: "number",
            PROP_REVIEW_AT: "date",
            # Note: PROP_LAST_UPDATED is page metadata, not a database property
        }

        missing = []
        wrong_type = []

        for prop_name, expected_type in required_props.items():
            if prop_name not in properties:
                missing.append(f"{prop_name} (expected: {expected_type})")
            else:
                prop = properties[prop_name]
                actual_type = prop.get("type")
                if actual_type != expected_type:
                    wrong_type.append(
                        f"{prop_name} (expected: {expected_type}, got: {actual_type})"
                    )

        if missing or wrong_type:
            error_msg = "Notion database schema mismatch:\n"
            if missing:
                error_msg += f"Missing properties: {', '.join(missing)}\n"
            if wrong_type:
                error_msg += f"Wrong types: {', '.join(wrong_type)}"
            logger.warning(error_msg)
            raise ValueError(error_msg)

        # Check status options
        status_prop = properties.get(PROP_STATUS, {})
        status_options = status_prop.get("select", {}).get("options", [])
        status_names = {opt.get("name") for opt in status_options}
        missing_statuses = STATUS_MAP - status_names
        if missing_statuses:
            logger.warning(
                f"Notion database missing status options: {', '.join(missing_statuses)}"
            )

        logger.info("Notion database schema validation passed")

    except APIResponseError as e:
        logger.error(f"Notion API error checking schema: {e.code} - {e.message} (request_id: {e.request_id})")
        raise ValueError(f"Notion API error: {e.message}") from e
    except Exception as e:
        logger.error(f"Error checking Notion schema: {e}")
        raise

