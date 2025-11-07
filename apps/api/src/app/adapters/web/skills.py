"""Skills router backed by provider with graceful fallbacks."""
from __future__ import annotations

from typing import List, Tuple, Union

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from app.core.settings import settings
from app.core.logging import get_logger
from app.providers.skills import (
    SkillOut,
    SkillsSourceMode,
    SkillsUnavailableError,
    get_last_fetch_meta,
    get_skills,
)


router = APIRouter(prefix="/api/skills", tags=["skills"])
logger = get_logger(__name__)


def _normalize_lang(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    lowered = value.strip().lower()
    if not lowered:
        return None
    if lowered.startswith("ru"):
        return "ru"
    if lowered.startswith("en"):
        return "en"
    return None


def _parse_accept_language(header_value: str | None) -> str | None:
    if not header_value:
        return None
    for chunk in header_value.split(","):
        lang_token = chunk.split(";", 1)[0].strip()
        normalized = _normalize_lang(lang_token)
        if normalized:
            return normalized
    return None


def _resolve_request_lang(request: Request, lang_param: str | None) -> Tuple[str, str]:
    candidate = _normalize_lang(lang_param)
    if candidate:
        return candidate, "query"

    header_candidate = _normalize_lang(request.headers.get("X-Locale"))
    if header_candidate:
        return header_candidate, "header"

    accept_candidate = _parse_accept_language(request.headers.get("Accept-Language"))
    if accept_candidate:
        return accept_candidate, "accept"

    return "en", "default"


def _resolve_source_mode() -> SkillsSourceMode:
    raw = (settings.skills_source or "auto").strip().lower()
    try:
        return SkillsSourceMode(raw)
    except ValueError:
        return SkillsSourceMode.AUTO


@router.get("", response_model=List[SkillOut])
async def list_skills(
    request: Request,
    lang: str | None = Query(None, pattern="^(?:en|ru|EN|RU)$", description="Locale code"),
) -> Union[List[SkillOut], JSONResponse]:
    normalized_lang, source = _resolve_request_lang(request, lang)
    logger.debug("skills.lang.resolve", extra={"resolved": normalized_lang, "source": source})
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
    request: Request,
    slug: str,
    lang: str | None = Query(None, pattern="^(?:en|ru|EN|RU)$", description="Locale code"),
) -> Union[SkillOut, JSONResponse]:
    normalized_lang, source = _resolve_request_lang(request, lang)
    logger.debug(
        "skills.lang.resolve.detail",
        extra={"resolved": normalized_lang, "source": source, "slug": slug},
    )

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
    async def debug_skills(
        request: Request,
        lang: str | None = Query(None, pattern="^(?:en|ru|EN|RU)$", description="Locale code"),
    ) -> JSONResponse:
        resolved_lang, source = _resolve_request_lang(request, lang)
        meta = get_last_fetch_meta()
        return JSONResponse(
            status_code=200,
            content={
                "resolved_lang": resolved_lang,
                "source": meta.source,
                "count": meta.count,
            },
        )




