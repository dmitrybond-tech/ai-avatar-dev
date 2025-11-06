from __future__ import annotations

import os
from typing import List, Optional, Tuple

from notion_client import Client, APIResponseError
from pydantic import BaseModel, Field


# Environment variables
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "").strip()
NOTION_PUBLIC_TASKS_DB_ID = os.getenv("NOTION_PUBLIC_TASKS_DB_ID", "").strip()
NOTION_TIMEOUT = int(os.getenv("NOTION_TIMEOUT", "10"))


def _validate_env() -> None:
    """Validate required environment variables. Raises ValueError if missing."""
    if not NOTION_API_KEY:
        raise ValueError("NOTION_API_KEY is not set")
    if not NOTION_PUBLIC_TASKS_DB_ID:
        raise ValueError("NOTION_PUBLIC_TASKS_DB_ID is not set")


def _client() -> Client:
    """Create and return a Notion client instance."""
    _validate_env()
    return Client(auth=NOTION_API_KEY, timeout_ms=NOTION_TIMEOUT * 1000)


class SchemaInfo:
    """Schema information for a Notion database."""
    def __init__(
        self,
        title_prop: str,
        public_prop: str,
        status_prop: str,
        status_type: str,  # "status" or "select"
        status_values: List[str],
    ):
        self.title_prop = title_prop
        self.public_prop = public_prop
        self.status_prop = status_prop
        self.status_type = status_type
        self.status_values = status_values


def resolve_schema(client: Client, dbid: str) -> SchemaInfo:
    """
    Resolve database schema and return property names and status options.
    
    Args:
        client: Notion client instance
        dbid: Database ID
        
    Returns:
        SchemaInfo with property names and status information
        
    Raises:
        APIResponseError: If database cannot be retrieved
    """
    db = client.databases.retrieve(database_id=dbid)
    props = db.get("properties", {})
    
    # Find title property (usually "Name" or "Title")
    title_prop = None
    for prop_name, prop_data in props.items():
        if prop_data.get("type") == "title":
            title_prop = prop_name
            break
    if not title_prop:
        raise ValueError("No title property found in database")
    
    # Find public checkbox property
    public_prop = None
    for prop_name, prop_data in props.items():
        if prop_data.get("type") == "checkbox":
            # Prefer "Public?" or "Public" but accept any checkbox
            if "public" in prop_name.lower():
                public_prop = prop_name
                break
    if not public_prop:
        # Try to find any checkbox as fallback
        for prop_name, prop_data in props.items():
            if prop_data.get("type") == "checkbox":
                public_prop = prop_name
                break
    if not public_prop:
        raise ValueError("No public checkbox property found in database")
    
    # Find status property (status or select type)
    status_prop = None
    status_type = None
    status_values = []
    
    for prop_name, prop_data in props.items():
        prop_type = prop_data.get("type")
        if prop_type == "status":
            status_prop = prop_name
            status_type = "status"
            options = prop_data.get("status", {}).get("options", [])
            status_values = [opt.get("name", "") for opt in options if opt.get("name")]
            break
        elif prop_type == "select":
            # Prefer status type, but accept select if no status found
            if not status_prop:
                status_prop = prop_name
                status_type = "select"
                options = prop_data.get("select", {}).get("options", [])
                status_values = [opt.get("name", "") for opt in options if opt.get("name")]
    
    if not status_prop:
        raise ValueError("No status or select property found in database")
    
    return SchemaInfo(
        title_prop=title_prop,
        public_prop=public_prop,
        status_prop=status_prop,
        status_type=status_type,
        status_values=status_values,
    )


def first_description(client: Client, page_id: str) -> Optional[str]:
    """
    Extract first paragraph or bullet text from a Notion page.
    Returns plain text up to 240 characters.
    
    Args:
        client: Notion client instance
        page_id: Page ID
        
    Returns:
        Plain text description or None
    """
    try:
        # Fetch page blocks
        blocks = client.blocks.children.list(block_id=page_id, page_size=30)
        
        for block in blocks.get("results", []):
            block_type = block.get("type")
            
            # Try paragraph first
            if block_type == "paragraph":
                rich_text = block.get("paragraph", {}).get("rich_text", [])
                text_parts = []
                for rt in rich_text:
                    plain = rt.get("plain_text", "")
                    if plain:
                        text_parts.append(plain)
                if text_parts:
                    desc = " ".join(text_parts).replace("\n", " ").replace("\r", " ").strip()
                    if desc:
                        return desc[:240]
            
            # Try bulleted list item
            elif block_type == "bulleted_list_item":
                rich_text = block.get("bulleted_list_item", {}).get("rich_text", [])
                text_parts = []
                for rt in rich_text:
                    plain = rt.get("plain_text", "")
                    if plain:
                        text_parts.append(plain)
                if text_parts:
                    desc = " ".join(text_parts).replace("\n", " ").replace("\r", " ").strip()
                    if desc:
                        return desc[:240]
    except Exception:
        # Fail silently if description extraction fails
        pass
    
    return None


def compute_progress(scope: Optional[float], done: Optional[float], fallback_pct: Optional[float] = None) -> int:
    """
    Compute progress percentage from scope/done, with fallback.
    Clamps result to 0..100.
    
    Args:
        scope: Scope value (number)
        done: Done value (number)
        fallback_pct: Fallback percentage if scope/done not available
        
    Returns:
        Progress percentage (0-100)
    """
    if scope is not None and done is not None:
        s = max(float(scope or 0), 0)
        d = max(float(done or 0), 0)
        if s > 0:
            return min(100, max(0, round(100 * d / s)))
    
    if fallback_pct is not None:
        return max(0, min(100, int(fallback_pct)))
    
    return 0


class PublicTaskOut(BaseModel):
    """Output model for public tasks."""
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


def _normalize_status(status: str) -> str:
    """Normalize status string for case-insensitive comparison."""
    return status.strip().lower()


def _find_matching_statuses(requested_statuses: List[str], available_statuses: List[str]) -> List[str]:
    """
    Find matching statuses from available options (case-insensitive).
    
    Args:
        requested_statuses: List of requested status names
        available_statuses: List of available status names from schema
        
    Returns:
        List of matching status names (using actual case from available_statuses)
    """
    if not requested_statuses:
        return []
    
    # Create normalized -> actual mapping
    status_map = {_normalize_status(s): s for s in available_statuses}
    
    matched = []
    for req in requested_statuses:
        normalized = _normalize_status(req)
        if normalized in status_map:
            matched.append(status_map[normalized])
    
    return matched


def query_public_tasks(statuses: Optional[List[str]] = None, limit: int = 20) -> List[PublicTaskOut]:
    """
    Query public tasks from Notion database.
    
    Args:
        statuses: Optional list of status names to filter by (case-insensitive)
        limit: Maximum number of tasks to return (default 20)
        
    Returns:
        List of PublicTaskOut objects
        
    Raises:
        ValueError: If environment variables are missing
        Exception: On Notion API errors
    """
    _validate_env()
    
    try:
        client = _client()
        schema = resolve_schema(client, NOTION_PUBLIC_TASKS_DB_ID)
    except ValueError as e:
        raise e
    except APIResponseError as e:
        raise Exception(f"Notion API error: {e}")
    except Exception as e:
        raise Exception(f"Failed to connect to Notion: {e}")
    
    # Build filter: always require public=true
    filters = [
        {"property": schema.public_prop, "checkbox": {"equals": True}}
    ]
    
    # Add status filter if statuses provided and they intersect with available options
    if statuses:
        matched_statuses = _find_matching_statuses(statuses, schema.status_values)
        if matched_statuses:
            if len(matched_statuses) == 1:
                if schema.status_type == "status":
                    filters.append({
                        "property": schema.status_prop,
                        "status": {"equals": matched_statuses[0]}
                    })
                else:
                    filters.append({
                        "property": schema.status_prop,
                        "select": {"equals": matched_statuses[0]}
                    })
            else:
                # Multiple statuses: use OR condition
                status_conditions = []
                for status in matched_statuses:
                    if schema.status_type == "status":
                        status_conditions.append({
                            "property": schema.status_prop,
                            "status": {"equals": status}
                        })
                    else:
                        status_conditions.append({
                            "property": schema.status_prop,
                            "select": {"equals": status}
                        })
                filters.append({"or": status_conditions})
    
    # Combine filters with AND
    query_filter = {"and": filters} if len(filters) > 1 else filters[0]
    
    # Query database
    results: List[dict] = []
    has_more = True
    cursor = None
    
    try:
        while has_more and len(results) < limit:
            query_params = {
                "database_id": NOTION_PUBLIC_TASKS_DB_ID,
                "filter": query_filter,
                "page_size": min(limit - len(results), 100),
                "sorts": [
                    {"property": "last_edited_time", "direction": "descending"}
                ],
            }
            if cursor:
                query_params["start_cursor"] = cursor
            
            resp = client.databases.query(**query_params)
            results.extend(resp.get("results", []))
            has_more = resp.get("has_more", False)
            cursor = resp.get("next_cursor")
    except APIResponseError as e:
        raise Exception(f"Notion query failed: {e}")
    except Exception as e:
        raise Exception(f"Failed to query Notion database: {e}")
    
    # Convert pages to PublicTaskOut
    tasks = []
    for page in results[:limit]:
        try:
            props = page.get("properties", {})
            page_id = page.get("id", "")
            
            # Extract title
            title_arr = props.get(schema.title_prop, {}).get("title", [])
            title = "".join(rt.get("plain_text", "") for rt in title_arr) or "Untitled"
            
            # Extract status
            status_prop_data = props.get(schema.status_prop, {})
            if schema.status_type == "status":
                status = (status_prop_data.get("status") or {}).get("name") or "Backlog"
            else:
                status = (status_prop_data.get("select") or {}).get("name") or "Backlog"
            
            # Extract scope and done (number properties)
            scope = None
            done = None
            progress_pct_prop = None
            
            # Try to find scope/done/progress properties by common names
            for prop_name, prop_data in props.items():
                prop_type = prop_data.get("type")
                if prop_type == "number":
                    prop_lower = prop_name.lower()
                    if "scope" in prop_lower:
                        scope = prop_data.get("number")
                    elif "done" in prop_lower:
                        done = prop_data.get("number")
                    elif "progress" in prop_lower and "%" in prop_name:
                        progress_pct_prop = prop_data.get("number")
            
            # Extract tags (multi_select)
            tags = []
            for prop_name, prop_data in props.items():
                if prop_data.get("type") == "multi_select":
                    multi_select = prop_data.get("multi_select", [])
                    tags = [opt.get("name", "") for opt in multi_select if opt.get("name")]
                    break
            
            # Extract reviewAt (date property)
            review_at = None
            for prop_name, prop_data in props.items():
                if prop_data.get("type") == "date":
                    date_data = prop_data.get("date")
                    if date_data and date_data.get("start"):
                        review_at = date_data.get("start")
                        break
            
            # Extract description
            description = first_description(client, page_id)
            
            # Compute progress
            progress_pct = compute_progress(scope, done, progress_pct_prop)
            
            # Generate URL
            url = f"https://notion.so/{page_id.replace('-', '')}"
            
            # Get last updated time
            last_updated = page.get("last_edited_time", "")
            
            tasks.append(PublicTaskOut(
                id=page_id,
                title=title,
                status=status,
                scope=int(scope) if scope is not None else None,
                done=int(done) if done is not None else None,
                progressPct=progress_pct,
                description=description,
                tags=tags,
                reviewAt=review_at,
                lastUpdated=last_updated,
                url=url,
            ))
        except Exception as e:
            # Log but continue processing other tasks
            import logging
            logging.warning(f"Failed to convert page {page.get('id', 'unknown')}: {e}")
            continue
    
    return tasks

