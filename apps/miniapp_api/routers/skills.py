from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from apps.miniapp_api.services.skills_loader import load_skills


router = APIRouter(prefix="/skills", tags=["skills"])


def _lang(v: Optional[str]) -> str:
    return "ru" if (v or "").lower().startswith("ru") else "en"


@router.get("")
def list_skills(lang: Optional[str] = Query(default=None)) -> List[Dict[str, object]]:
    return load_skills(_lang(lang))


@router.get("/{slug}")
def get_skill(slug: str, lang: Optional[str] = Query(default=None)) -> Dict[str, object]:
    for s in load_skills(_lang(lang)):
        if s.get("slug") == slug:
            return s
    raise HTTPException(status_code=404, detail="Skill not found")


