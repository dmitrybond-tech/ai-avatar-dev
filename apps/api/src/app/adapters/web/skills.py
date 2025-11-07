"""Skills router backed by Notion database."""
from __future__ import annotations

from dataclasses import asdict
from typing import List

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from app.core.settings import settings
from app.integrations.notion_skills import (
    Lang,
    NotionConfigError,
    NotionServiceError,
    fetch_skill_by_slug,
    fetch_skills,
)
from app.schemas.skills import SkillOut


router = APIRouter(prefix="/api/skills", tags=["skills"])


def _normalize_lang(value: str | None) -> Lang:
    if isinstance(value, str) and value.strip().lower() == "ru":
        return "ru"
    return "en"


def _ensure_configured() -> None:
    if not settings.notion_api_key or not settings.notion_skills_db_id:
        raise NotionConfigError("Notion skills integration is not configured")


@router.get("", response_model=List[SkillOut])
async def list_skills(lang: str = Query("en", pattern="^(?:en|ru|EN|RU)$", description="Locale code")) -> List[SkillOut]:
    normalized_lang = _normalize_lang(lang)

    try:
        _ensure_configured()
        records = await run_in_threadpool(lambda: fetch_skills(normalized_lang))
        return [SkillOut.model_validate(asdict(record)) for record in records]
    except NotionConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except NotionServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{slug}", response_model=SkillOut)
async def get_skill(slug: str, lang: str = Query("en", pattern="^(?:en|ru|EN|RU)$", description="Locale code")) -> SkillOut:
    normalized_lang = _normalize_lang(lang)

    try:
        _ensure_configured()
        record = await run_in_threadpool(lambda: fetch_skill_by_slug(slug, normalized_lang))
    except NotionConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except NotionServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if record is None:
        raise HTTPException(status_code=404, detail="Skill not found")

    return SkillOut.model_validate(asdict(record))



