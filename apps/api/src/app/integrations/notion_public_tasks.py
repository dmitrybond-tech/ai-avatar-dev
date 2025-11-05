"""Notion integration for Public On-Board Tasks."""
from datetime import datetime
from typing import Optional, List
from notion_client import Client, APIResponseError
from pydantic import BaseModel, Field, field_validator
from app.core.settings import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

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

# Initialize Notion client
_notion_client: Optional[Client] = None


def get_notion_client() -> Client:
    """Get or create Notion client instance."""
    global _notion_client
    if _notion_client is None:
        if not settings.notion_api_key:
            raise ValueError("NOTION_API_KEY is not set")
        _notion_client = Client(
            auth=settings.notion_api_key,
            timeout_ms=settings.notion_timeout * 1000,
        )
    return _notion_client


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


def query_public_tasks(limit: int = 100) -> List[PublicTaskOut]:
    """Query public tasks from Notion database."""
    client = get_notion_client()
    db_id = settings.notion_public_tasks_db_id

    if not db_id:
        raise ValueError("NOTION_PUBLIC_TASKS_DB_ID is not set")

    try:
        results = []
        has_more = True
        start_cursor = None

        while has_more and len(results) < limit:
            query_params = {
                "database_id": db_id,
                "filter": {
                    "property": PROP_PUBLIC,
                    "checkbox": {"equals": True},
                },
                "sorts": [
                    {"property": PROP_LAST_UPDATED, "direction": "descending"},
                    {"property": PROP_REVIEW_AT, "direction": "ascending"},
                ],
                "page_size": min(limit, 100),  # Notion API limit
            }
            if start_cursor:
                query_params["start_cursor"] = start_cursor

            response = client.databases.query(**query_params)
            pages = response.get("results", [])
            results.extend(pages)

            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")

        # Convert to PublicTaskOut and limit results
        tasks = [_page_to_public_task_out(page) for page in results[:limit]]
        return tasks

    except APIResponseError as e:
        logger.error(f"Notion API error: {e.code} - {e.message} (request_id: {e.request_id})")
        raise ValueError(f"Notion API error: {e.message}") from e
    except Exception as e:
        logger.error(f"Error querying Notion tasks: {e}")
        raise


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

