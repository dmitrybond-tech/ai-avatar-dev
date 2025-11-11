from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from ..core import env as env_utils
from ..integrations.notion_public import _client, query_public_tasks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskItem(BaseModel):
    id: str
    title: str
    status: Literal["todo", "in_progress", "done"]
    updatedAt: str


class TasksStatusResponse(BaseModel):
    items: List[TaskItem] = Field(default_factory=list)


def _set_tasks_state(request: Request, state: str) -> None:
    try:
        request.app.state.tasks_state = state
    except AttributeError:
        request.app.state.tasks_state = state


def _normalize_status(value: str) -> Literal["todo", "in_progress", "done"]:
    normalized = (value or "").strip().lower()
    if normalized in {"done", "completed", "complete", "shipped", "closed"}:
        return "done"
    if normalized in {"in progress", "progress", "doing", "active", "review", "blocked"}:
        return "in_progress"
    return "todo"


@router.get("/status", response_model=TasksStatusResponse)
def tasks_status(request: Request) -> TasksStatusResponse:
    dbid = env_utils.tasks_db()
    if not dbid:
        logger.warning("Notion tasks DB is not configured; returning empty list")
        _set_tasks_state(request, "degraded")
        return TasksStatusResponse()

    try:
        client = _client()
    except Exception as exc:  # pragma: no cover - network/client failure
        logger.warning("Notion client unavailable: %s", exc)
        _set_tasks_state(request, "degraded")
        return TasksStatusResponse()

    try:
        results = query_public_tasks(client, dbid, statuses=None, limit=20)
    except Exception as exc:  # pragma: no cover - Notion query failure
        logger.warning("Failed to query Notion public tasks: %s", exc)
        _set_tasks_state(request, "degraded")
        return TasksStatusResponse()

    items: List[TaskItem] = []
    for idx, item in enumerate(results):
        status = _normalize_status(str(item.get("status", "")))
        last_edited = str(item.get("lastEdited") or "").strip()
        if not last_edited:
            last_edited = datetime.now(timezone.utc).isoformat()
        task_id = str(item.get("id") or f"task-{idx}")
        title = str(item.get("title") or "Untitled").strip() or "Untitled"
        items.append(TaskItem(id=task_id, title=title, status=status, updatedAt=last_edited))

    _set_tasks_state(request, "ok")
    return TasksStatusResponse(items=items)
