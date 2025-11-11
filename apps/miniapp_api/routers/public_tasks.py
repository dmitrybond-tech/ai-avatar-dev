++@@
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from apps.miniapp_api.core import env as env_utils
from apps.miniapp_api.integrations.notion_public import _client, query_public_tasks, resolve_schema

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["public-tasks"])


def _mark_state(request: Request, ok: bool) -> None:
    state = "ok" if ok else "degraded"
    try:
        request.app.state.tasks_state = state
    except AttributeError:
        request.app.state.tasks_state = state


@router.get("/public")
def list_public_tasks(
    request: Request,
    statuses: Optional[str] = Query(default=None, description="Comma-separated statuses, e.g. 'In Progress,Review'"),
    limit: int = Query(default=20, ge=1, le=50, description="Max number of tasks (1..50)"),
) -> List[dict]:
    dbid = env_utils.tasks_db()
    if not dbid:
        logger.warning("Notion public tasks DB is not configured; returning empty list.")
        _mark_state(request, False)
        return []
    try:
        client = _client()
    except ValueError:
        logger.warning("Notion credentials missing; returning empty public tasks list.")
        _mark_state(request, False)
        return []
    except Exception as exc:  # pragma: no cover - optional network failure
        logger.warning("Failed to initialize Notion client: %s", exc)
        _mark_state(request, False)
        return []

    try:
        parsed: Optional[List[str]] = None
        if statuses and statuses.strip():
            parsed = [s.strip() for s in statuses.split(",") if s.strip()]
        if not parsed:
            parsed = ["In Progress", "Review"]
        data = query_public_tasks(client, dbid, parsed, limit)
        _mark_state(request, True)
        return data
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": "bad_request"}) from None
    except Exception as exc:
        logger.warning("Failed to query Notion public tasks: %s", exc)
        _mark_state(request, False)
        return []


@router.get("/debug")
def debug_tasks(request: Request) -> dict:
    try:
        dbid = env_utils.tasks_db()
        if not dbid:
            _mark_state(request, False)
            return {"titleProp": None, "publicProp": None, "statusProp": None, "statusValues": []}
        client = _client()
        schema = resolve_schema(client, dbid)
        _mark_state(request, True)
        return {
            "titleProp": schema["title_prop"],
            "publicProp": schema["public_prop"],
            "statusProp": schema["status_prop"],
            "statusValues": schema["status_values"],
        }
    except HTTPException:
        _mark_state(request, False)
        return {"titleProp": None, "publicProp": None, "statusProp": None, "statusValues": []}
    except Exception:
        _mark_state(request, False)
        return {"titleProp": None, "publicProp": None, "statusProp": None, "statusValues": []}
