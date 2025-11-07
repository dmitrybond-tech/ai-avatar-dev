"""Skills router backed by provider with graceful fallbacks."""
from __future__ import annotations

from typing import List, Union

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from app.core.settings import settings
from app.providers.skills import (
    SkillOut,
    SkillsSourceMode,
    SkillsUnavailableError,
    get_last_fetch_meta,
    get_skills,
)


router = APIRouter(prefix="/api/skills", tags=["skills"])


def _normalize_lang(value: str | None) -> str:
    if isinstance(value, str) and value.strip().lower() == "ru":
        return "ru"
    return "en"


def _resolve_source_mode() -> SkillsSourceMode:
    raw = (settings.skills_source or "auto").strip().lower()
    try:
        return SkillsSourceMode(raw)
    except ValueError:
        return SkillsSourceMode.AUTO


@router.get("", response_model=List[SkillOut])
async def list_skills(
    lang: str = Query("en", pattern="^(?:en|ru|EN|RU)$", description="Locale code"),
) -> Union[List[SkillOut], JSONResponse]:
    normalized_lang = _normalize_lang(lang)
    source_mode = _resolve_source_mode()

    try:
        return await run_in_threadpool(lambda: get_skills(normalized_lang))
    except SkillsUnavailableError as exc:
        if source_mode is SkillsSourceMode.NOTION:
            return JSONResponse(status_code=503, content={"error": "notion_failed"})
        if source_mode is SkillsSourceMode.CSV:
            return JSONResponse(status_code=503, content={"error": "csv_failed"})
        raise HTTPException(status_code=503, detail="skills_unavailable") from exc


@router.get("/{slug}", response_model=SkillOut)
async def get_skill(
    slug: str,
    lang: str = Query("en", pattern="^(?:en|ru|EN|RU)$", description="Locale code"),
) -> Union[SkillOut, JSONResponse]:
    normalized_lang = _normalize_lang(lang)

    source_mode = _resolve_source_mode()

    try:
        skills = await run_in_threadpool(lambda: get_skills(normalized_lang))
    except SkillsUnavailableError as exc:
        if source_mode is SkillsSourceMode.NOTION:
            return JSONResponse(status_code=503, content={"error": "notion_failed"})
        if source_mode is SkillsSourceMode.CSV:
            return JSONResponse(status_code=503, content={"error": "csv_failed"})
        raise HTTPException(status_code=503, detail="skills_unavailable") from exc

    for item in skills:
        if item.slug.lower() == slug.strip().lower():
            return item
    raise HTTPException(status_code=404, detail="Skill not found")


if settings.debug_skills_api:

    @router.get("/_debug")
    async def debug_skills() -> JSONResponse:
        meta = get_last_fetch_meta()
        source = meta.source
        if meta.fallback and source == "csv":
            source = "auto(notion→csv)"
        return JSONResponse(status_code=200, content={"source": source, "count": meta.count})




