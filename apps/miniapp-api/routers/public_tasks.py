from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..integrations.notion_public import _client, resolve_schema, query_public_tasks

import os


router = APIRouter(prefix="/tasks", tags=["public-tasks"])


@router.get("/public")
def list_public_tasks(
    statuses: Optional[str] = Query(default=None, description="Comma-separated list of statuses (e.g., 'In Progress,Review')"),
    limit: int = Query(default=20, ge=1, le=50, description="Max number of tasks (1..50)"),
) -> List[dict]:
    try:
        # Support legacy env var: NOTION_DB → NOTION_PUBLIC_TASKS_DB_ID
        dbid = os.getenv("NOTION_PUBLIC_TASKS_DB_ID", "").strip() or os.getenv("NOTION_DB", "").strip()
        if not dbid:
            raise HTTPException(status_code=502, detail={"error": "notion_unreachable"})
        parsed: Optional[List[str]] = None
        if statuses and statuses.strip():
            parsed = [s.strip() for s in statuses.split(",") if s.strip()]
        if not parsed:
            parsed = ["In Progress", "Review"]
        c = _client()
        return query_public_tasks(c, dbid, parsed, limit)
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": "bad_request"})
    except Exception:
        raise HTTPException(status_code=502, detail={"error": "notion_unreachable"})


@router.get("/debug")
def debug_tasks() -> dict:
    try:
        # Support legacy env var: NOTION_DB → NOTION_PUBLIC_TASKS_DB_ID
        dbid = os.getenv("NOTION_PUBLIC_TASKS_DB_ID", "").strip() or os.getenv("NOTION_DB", "").strip()
        if not dbid:
            return {"titleProp": None, "publicProp": None, "statusProp": None, "statusValues": []}
        c = _client()
        schema = resolve_schema(c, dbid)
        return {
            "titleProp": schema["title_prop"],
            "publicProp": schema["public_prop"],
            "statusProp": schema["status_prop"],
            "statusValues": schema["status_values"],
        }
    except Exception:
        return {"titleProp": None, "publicProp": None, "statusProp": None, "statusValues": []}


