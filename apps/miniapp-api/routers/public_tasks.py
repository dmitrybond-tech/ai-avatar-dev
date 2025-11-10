from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..core import env as env_utils
from ..integrations.notion_public import _client, resolve_schema, query_public_tasks

router = APIRouter(prefix="/tasks", tags=["public-tasks"])


def _resolve_dbid() -> str:
    dbid = env_utils.tasks_db()
    if not dbid:
        raise HTTPException(status_code=502, detail={"error": "notion_unreachable"})
    return dbid


@router.get("/public")
def list_public_tasks(
    statuses: Optional[str] = Query(default=None, description="Comma-separated list of statuses (e.g., 'In Progress,Review')"),
    limit: int = Query(default=20, ge=1, le=50, description="Max number of tasks (1..50)"),
) -> List[dict]:
    try:
        dbid = _resolve_dbid()
        parsed: Optional[List[str]] = None
        if statuses and statuses.strip():
            parsed = [s.strip() for s in statuses.split(",") if s.strip()]
        if not parsed:
            parsed = ["In Progress", "Review"]
        client = _client()
        return query_public_tasks(client, dbid, parsed, limit)
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": "bad_request"})
    except Exception:
        raise HTTPException(status_code=502, detail={"error": "notion_unreachable"})


@router.get("/debug")
def debug_tasks() -> dict:
    try:
        dbid = _resolve_dbid()
        client = _client()
        schema = resolve_schema(client, dbid)
        return {
            "titleProp": schema["title_prop"],
            "publicProp": schema["public_prop"],
            "statusProp": schema["status_prop"],
            "statusValues": schema["status_values"],
        }
    except HTTPException:
        return {"titleProp": None, "publicProp": None, "statusProp": None, "statusValues": []}
    except Exception:
        return {"titleProp": None, "publicProp": None, "statusProp": None, "statusValues": []}

