from typing import List

from fastapi import APIRouter, HTTPException

from apps.miniapp_api.integrations.notion_public_tasks import (
    PublicTaskOut,
    PublicTaskCreate,
    PublicTaskUpdate,
    query_public_tasks,
    create_task,
    update_task,
    add_comment,
    assert_schema,
)


router = APIRouter(prefix="/tasks", tags=["public-tasks"])


@router.on_event("startup")
def _startup_check() -> None:
    try:
        assert_schema()
    except Exception:
        # Log-only behavior; do not crash app if Notion not configured
        pass


@router.get("/public", response_model=List[PublicTaskOut])
def list_public_tasks() -> List[PublicTaskOut]:
    try:
        return query_public_tasks(limit=100)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=PublicTaskOut)
def create_public_task(data: PublicTaskCreate) -> PublicTaskOut:
    try:
        return create_task(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{page_id}", response_model=PublicTaskOut)
def patch_task(page_id: str, data: PublicTaskUpdate) -> PublicTaskOut:
    try:
        return update_task(page_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{page_id}/comment")
def post_comment(page_id: str, payload: dict) -> dict:
    text = str(payload.get("text", "")).strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    try:
        add_comment(page_id, text)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


