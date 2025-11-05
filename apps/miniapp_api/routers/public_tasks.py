from typing import List

from fastapi import APIRouter, HTTPException

from apps.miniapp_api.integrations.notion_public_tasks import (
    PublicTaskOut,
    query_public_tasks,
)


router = APIRouter(prefix="/tasks")


@router.get("/public", response_model=List[PublicTaskOut])
def list_public() -> List[PublicTaskOut]:
    try:
        return query_public_tasks()
    except Exception as e:  # noqa: BLE001 - surface integration errors as 500
        raise HTTPException(status_code=500, detail=str(e))


