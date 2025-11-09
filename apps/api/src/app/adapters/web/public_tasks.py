"""Public tasks router for Notion integration."""
from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Header, Query, Response
from app.schemas.public_tasks import (
    PublicTaskOut,
    PublicTaskCreate,
    PublicTaskUpdate,
    CommentRequest,
)
from app.integrations.notion_public_tasks import (
    get_tasks_cache_snapshot,
    query_public_tasks,
    create_task,
    update_task,
    add_comment,
)
from app.core.settings import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

# Simple bearer token auth (can be enhanced with existing auth scheme)
AUTH_TOKEN = settings.jwt_secret  # Reuse JWT secret for simplicity, or add separate NOTION_AUTH_TOKEN


def verify_auth(authorization: str = Header(None)) -> None:
    """Verify bearer token for protected endpoints."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    token = authorization.replace("Bearer ", "")
    if token != AUTH_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")


def _resolve_locale_param(locale: Optional[str], accept_language: Optional[str]) -> Optional[str]:
    if locale:
        return locale
    if accept_language:
        return accept_language.split(",", 1)[0]
    return None


@router.get("/public", response_model=List[PublicTaskOut])
async def list_public_tasks(
    response: Response,
    limit: int = 100,
    locale: Optional[str] = Query(default=None, min_length=1),
    accept_language: Optional[str] = Header(default=None),
):
    """List public tasks from Notion database."""
    try:
        if limit < 1 or limit > 1000:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 1000")
        resolved_locale = _resolve_locale_param(locale, accept_language)
        cache_meta: dict[str, object] = {}
        tasks = query_public_tasks(limit=limit, locale=resolved_locale, meta=cache_meta)
        if cache_meta:
            header_value = '{"stale": true}' if cache_meta.get("stale") else '{"stale": false}'
            response.headers["X-Tasks-Cache"] = header_value
        return tasks
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing public tasks: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("", response_model=PublicTaskOut)
async def create_new_task(
    task: PublicTaskCreate,
    authorization: str = Header(None),
):
    """Create a new task in Notion."""
    try:
        # Optional auth - if token provided, verify it
        if authorization:
            try:
                verify_auth(authorization)
            except HTTPException:
                # If auth fails but token provided, reject
                raise

        # Validate input length
        if len(task.title) > 200:
            raise HTTPException(status_code=400, detail="Title too long (max 200 characters)")

        created = create_task(
            title=task.title,
            status=task.status,
            scope=task.scope,
            done=task.done,
            review_at=task.review_at,
            tags=task.tags,
            source=task.source,
        )
        return created
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/{task_id}", response_model=PublicTaskOut)
async def update_existing_task(
    task_id: str,
    task_update: PublicTaskUpdate,
    authorization: str = Header(None),
):
    """Update an existing task in Notion."""
    try:
        # Require auth for updates
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization required for updates")
        verify_auth(authorization)

        # Validate input length
        if task_update.title and len(task_update.title) > 200:
            raise HTTPException(status_code=400, detail="Title too long (max 200 characters)")

        updated = update_task(
            notion_page_id=task_id,
            title=task_update.title,
            status=task_update.status,
            scope=task_update.scope,
            done=task_update.done,
            review_at=task_update.review_at,
            tags=task_update.tags,
        )
        return updated
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{task_id}/comment")
async def add_task_comment(
    task_id: str,
    comment: CommentRequest,
    authorization: str = Header(None),
):
    """Add an internal comment to a Notion task."""
    try:
        # Require auth for comments
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization required for comments")
        verify_auth(authorization)

        # Validate input length
        if len(comment.text) > 1000:
            raise HTTPException(status_code=400, detail="Comment too long (max 1000 characters)")

        add_comment(notion_page_id=task_id, text=comment.text)
        return {"status": "ok", "message": "Comment added"}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding comment: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/_debug")
async def tasks_debug(locale: Optional[str] = Query(default=None, min_length=1)):
    """Expose tasks cache/debug info without hitting Notion."""
    resolved_locale = _resolve_locale_param(locale, None)
    snapshot = get_tasks_cache_snapshot(resolved_locale)
    raw_ttl = getattr(settings, "notion_cache_ttl_tasks", 300)
    try:
        cache_ttl = int(raw_ttl)
    except (TypeError, ValueError):
        cache_ttl = raw_ttl
    return {
        "has_api_key": bool((settings.notion_api_key or "").strip()),
        "has_db_id": bool((settings.notion_public_tasks_db_id or "").strip()),
        "cache_ttl": cache_ttl,
        "count": snapshot["count"],
        "last_updated": snapshot["last_updated"],
    }

