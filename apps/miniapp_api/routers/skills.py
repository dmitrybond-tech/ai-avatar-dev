from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.responses import JSONResponse

from notion_client import Client

from apps.miniapp_api.core.settings import SettingsError
from apps.miniapp_api.routers.deps import get_settings
from apps.miniapp_api.services.skills_repo import Skill, SkillsRepository


logger = logging.getLogger(__name__)

router = APIRouter(tags=["skills"])


def _normalize_lang(value: Optional[str]) -> str:
    return "ru" if (value or "").lower().startswith("ru") else "en"


@lru_cache(maxsize=4)
def _build_repo(token: str, db_id: str, timeout: int) -> SkillsRepository:
    client = Client(auth=token, timeout=timeout)
    return SkillsRepository(client, db_id, timeout=timeout)


def get_repo(settings=Depends(get_settings)) -> SkillsRepository:  # type: ignore[override]
    try:
        settings.ensure_skills_config()
    except SettingsError as exc:
        logger.error("skills configuration missing: %s", exc)
        raise HTTPException(status_code=500, detail="skills_config_missing") from exc

    token = settings.notion_token
    db_id = settings.NOTION_DB_SKILLS
    if not token or not db_id:
        raise HTTPException(status_code=500, detail="skills_config_missing")

    try:
        return _build_repo(token, db_id, settings.NOTION_TIMEOUT)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("failed to build skills repository")
        raise HTTPException(status_code=502, detail=f"notion_error:{exc.__class__.__name__}") from exc


def _serialize(skill: Skill) -> Dict[str, Any]:
    data = skill.dict()
    if not data.get("short"):
        data["short"] = ""
    if not data.get("long"):
        data["long"] = None
    return data


@router.get("/skills")
def skills(
    lang: str = Query("en", description="Language code (ru|en)"),
    _debug: int = Query(0, description="Return JSONResponse payload when set"),
    repo: SkillsRepository = Depends(get_repo),
):
    resolved_lang = _normalize_lang(lang)
    try:
        items, meta = repo.get_skills(resolved_lang)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("skills_fetch_failed lang=%s", resolved_lang)
        raise HTTPException(status_code=502, detail=f"notion_error:{exc.__class__.__name__}") from exc

    payload = {
        "items": [_serialize(item) for item in items],
        "meta": {"lang": resolved_lang, **meta},
    }
    if _debug:
        return JSONResponse(payload)
    return payload


@router.get("/skills/{slug}")
def skill_detail(
    slug: str,
    lang: str = Query("en", description="Language code (ru|en)"),
    repo: SkillsRepository = Depends(get_repo),
):
    resolved_lang = _normalize_lang(lang)
    items, _ = repo.get_skills(resolved_lang)
    for item in items:
        if item.slug == slug or item.id == slug:
            return _serialize(item)
    raise HTTPException(status_code=404, detail="skill_not_found")


@router.get("/_health/skills")
def skills_health(settings=Depends(get_settings)):
    try:
        settings.ensure_skills_config()
    except SettingsError as exc:
        logger.error("skills health check failed: %s", exc)
        raise HTTPException(status_code=500, detail="skills_config_missing") from exc
    return {"ok": True}


