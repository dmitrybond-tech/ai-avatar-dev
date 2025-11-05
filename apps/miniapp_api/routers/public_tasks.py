from typing import List, Dict

from fastapi import APIRouter


router = APIRouter(prefix="/tasks", tags=["public-tasks"])


@router.get("/public", response_model=List[Dict])
def list_public() -> List[Dict]:
    # Minimal read-only endpoint for now; integrate Notion later
    return []


