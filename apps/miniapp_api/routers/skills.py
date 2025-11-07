from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from notion_client import Client
from pydantic import ValidationError

from apps.miniapp_api.core.settings import get_settings
from apps.miniapp_api.services.skills_repo import Skill, SkillsRepository


log = logging.getLogger(__name__)

router = APIRouter(tags=["skills"])


def _normalize_lang(value: Optional[str]) -> str:
    return "ru" if (value or "").lower().startswith("ru") else "en"


def _build_repo_or_raise() -> SkillsRepository:
    try:
        settings = get_settings()
        db_id = settings.NOTION_DB_SKILLS
        token = getattr(settings, "NOTION_API_KEY", None) or getattr(settings, "NOTION_SECRET", None)
        if not token or not db_id:
            raise HTTPException(status_code=500, detail="skills_config_missing")

        timeout = getattr(settings, "NOTION_TIMEOUT", 10)
        client = Client(auth=token, timeout=timeout)
        return SkillsRepository(client, db_id, timeout)
    except ValidationError:
        log.exception("skills_settings_validation_failed")
        raise HTTPException(status_code=500, detail="skills_settings_invalid")
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        log.exception("skills_repo_init_failed")
        raise HTTPException(status_code=500, detail=f"skills_repo_init_failed:{exc.__class__.__name__}") from exc


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
    _debug: int = Query(0, description="Return raw payload when set"),
):
    resolved_lang = _normalize_lang(lang)

    repo = _build_repo_or_raise()

    try:
        items, meta = repo.get_skills(resolved_lang)
    except Exception as exc:  # noqa: BLE001
        log.exception("skills_fetch_failed")
        detail = f"notion_error:{exc.__class__.__name__}"
        if _debug:
            return {"items": [], "meta": {"lang": resolved_lang, "error": detail}}
        raise HTTPException(status_code=502, detail=detail) from exc

    payload = {
        "items": [_serialize(item) for item in items],
        "meta": {"lang": resolved_lang, **meta},
    }
    return payload


@router.get("/skills/{slug}")
def skill_detail(
    slug: str,
    lang: str = Query("en", description="Language code (ru|en)"),
):
    resolved_lang = _normalize_lang(lang)
    repo = _build_repo_or_raise()
    try:
        items, _ = repo.get_skills(resolved_lang)
    except Exception as exc:  # noqa: BLE001
        log.exception("skills_fetch_failed")
        raise HTTPException(status_code=502, detail=f"notion_error:{exc.__class__.__name__}") from exc
    for item in items:
        if item.slug == slug or item.id == slug:
            return _serialize(item)
    raise HTTPException(status_code=404, detail="skill_not_found")


@router.get("/_health/skills")
def health_skills() -> Dict[str, Any]:
    try:
        settings = get_settings()
        return {
            "ok": True,
            "env": {
                "has_db_id": bool(getattr(settings, "NOTION_DB_SKILLS", None)),
                "has_token": bool(
                    getattr(settings, "NOTION_API_KEY", None) or getattr(settings, "NOTION_SECRET", None)
                ),
            },
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": exc.__class__.__name__}


