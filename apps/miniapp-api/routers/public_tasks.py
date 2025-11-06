from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from notion_client import APIResponseError

# Use relative imports to survive dash/underscore copy
from ..integrations.notion_public_tasks import (
    PublicTaskOut,
    PublicTaskCreate,
    PublicTaskUpdate,
    query_public_tasks,
    create_task,
    update_task,
    add_comment,
    assert_schema,
    NOTION_PUBLIC_TASKS_DB_ID,
    _get_status_mapping,
    _client,
)


router = APIRouter(prefix="/tasks", tags=["public-tasks"])


@router.on_event("startup")
def _startup_check() -> None:
    """Validate Notion schema on startup (non-blocking)."""
    try:
        assert_schema()
    except Exception:
        # Log-only behavior; do not crash app if Notion not configured
        pass


@router.get("/public", response_model=List[PublicTaskOut])
def list_public_tasks(
    statuses: Optional[str] = Query(default=None, description="Comma-separated list of status names (e.g., 'In Progress,Review')"),
    open_only: bool = Query(default=True, description="Exclude Done/Closed and items with progressPct >= 100"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of tasks to return")
) -> List[PublicTaskOut]:
    """
    List public tasks from Notion.
    Default filter: Public? = true and Status in {In Progress, Review} (or progressPct < 100 if no status match).
    """
    try:
        # Parse statuses CSV if provided
        parsed_statuses = None
        if statuses:
            parsed_statuses = [s.strip() for s in statuses.split(",") if s.strip()]
            if not parsed_statuses:
                parsed_statuses = None
        
        # Default statuses when open_only=True and no statuses specified
        if open_only and parsed_statuses is None:
            parsed_statuses = ["In Progress", "Review"]
        
        return query_public_tasks(limit=limit, statuses=parsed_statuses, open_only=open_only)
    except ValueError as e:
        # Missing configuration - return 500
        raise HTTPException(status_code=500, detail="Notion configuration error")
    except APIResponseError as e:
        # Notion API error - return 502
        raise HTTPException(status_code=502, detail="Notion query failed")
    except Exception as e:
        # Other errors - return 502 with safe message
        raise HTTPException(status_code=502, detail="Notion query failed")


@router.post("/", response_model=PublicTaskOut)
def create_public_task(data: PublicTaskCreate) -> PublicTaskOut:
    try:
        return create_task(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{id}", response_model=PublicTaskOut)
def patch_task(id: str, data: PublicTaskUpdate) -> PublicTaskOut:
    try:
        return update_task(id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{id}/comment")
def post_comment(id: str, payload: dict) -> dict:
    """Add an internal Notion comment to a task page."""
    text = str(payload.get("text", "")).strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    try:
        add_comment(id, text)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debug")
def debug_tasks() -> dict:
    """
    Debug endpoint to check Notion configuration and available status values.
    Does not expose secrets.
    """
    try:
        configured = bool(NOTION_PUBLIC_TASKS_DB_ID)
        status_values = []
        
        if configured:
            try:
                c = _client()
                is_status_type, status_mapping = _get_status_mapping(c)
                status_values = sorted(status_mapping.values())
            except Exception:
                pass  # Don't fail if we can't fetch
        
        return {
            "db": NOTION_PUBLIC_TASKS_DB_ID if configured else None,
            "configured": configured,
            "statusValues": status_values,
        }
    except Exception:
        return {
            "db": None,
            "configured": False,
            "statusValues": [],
        }


