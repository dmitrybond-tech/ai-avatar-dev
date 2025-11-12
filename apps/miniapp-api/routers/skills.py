from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from ..services.skills import SkillRecord, SkillsRepository

router = APIRouter(tags=["skills"])
api_router = APIRouter(prefix="/api", tags=["skills"])
alias_router = APIRouter(tags=["legacy-rules"])


def _lang_key(lang: Optional[str]) -> str:
    if not lang:
        return "en"
    return "ru" if lang.lower().startswith("ru") else "en"


def _repo(request: Request) -> SkillsRepository:
    repo = getattr(request.app.state, "skills_repo", None)
    if repo is None:
        raise RuntimeError("skills repository not initialized")
    return repo


def _project_card(skill: SkillRecord, lang: str) -> Dict[str, Any]:
    return {
        "slug": skill.key,
        "title": skill.title(lang),
        "short": skill.summary(lang),
        "tags": skill.tags,
    }


def _project_detail(skill: SkillRecord, lang: str) -> Dict[str, Any]:
    return {
        "slug": skill.key,
        "title": skill.title(lang),
        "short": skill.summary(lang),
        "tags": skill.tags,
        "bullets": skill.bullets(lang),
        "examples": skill.examples(lang),
    }


def _list_skills_impl(request: Request, lang: Optional[str]) -> List[Dict[str, Any]]:
    repo = _repo(request)
    snapshot = repo.snapshot()
    skills = snapshot.skills
    if not skills:
        return []
    lang_key = _lang_key(lang)
    if lang:
        return [_project_card(skill, lang_key) for skill in skills]
    return [
        {
            "slug": skill.key,
            "title_en": skill.title("en"),
            "title_ru": skill.title("ru"),
            "short_en": skill.summary("en"),
            "short_ru": skill.summary("ru"),
            "tags": skill.tags,
            "bullets_en": skill.bullets("en"),
            "bullets_ru": skill.bullets("ru"),
            "examples_en": skill.examples("en"),
            "examples_ru": skill.examples("ru"),
        }
        for skill in skills
    ]


def _get_skill_impl(
    slug: str,
    request: Request,
    lang: Optional[str],
) -> Dict[str, Any]:
    repo = _repo(request)
    snapshot = repo.snapshot()
    skill = next((item for item in snapshot.skills if item.key == slug), None)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    if lang:
        return _project_detail(skill, _lang_key(lang))
    return {
        "slug": skill.key,
        "title_en": skill.title("en"),
        "title_ru": skill.title("ru"),
        "short_en": skill.summary("en"),
        "short_ru": skill.summary("ru"),
        "tags": skill.tags,
        "bullets_en": skill.bullets("en"),
        "bullets_ru": skill.bullets("ru"),
        "examples_en": skill.examples("en"),
        "examples_ru": skill.examples("ru"),
    }


@router.get("/skills")
def list_skills(
    request: Request,
    lang: Optional[str] = Query(default=None, description="ru|en for projected payload"),
) -> List[Dict[str, Any]]:
    return _list_skills_impl(request=request, lang=lang)


@router.get("/skills/{slug}")
def get_skill(
    slug: str,
    request: Request,
    lang: Optional[str] = Query(default=None, description="ru|en for projected payload"),
) -> Dict[str, Any]:
    return _get_skill_impl(slug=slug, request=request, lang=lang)


@alias_router.get("/rules")
def rules_alias(
    request: Request,
    lang: Optional[str] = Query(default=None),
) -> List[Dict[str, Any]]:
    return _list_skills_impl(request=request, lang=lang)


@alias_router.get("/rules/{slug}")
def rules_detail_alias(
    slug: str,
    request: Request,
    lang: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    return _get_skill_impl(slug=slug, request=request, lang=lang)


@api_router.get("/skills")
def list_skills_api(
    request: Request,
    lang: Optional[str] = Query(default=None, description="ru|en for projected payload"),
) -> List[Dict[str, Any]]:
    return _list_skills_impl(request=request, lang=lang)


@api_router.get("/skills/debug")
def debug_skills(request: Request) -> Dict[str, Any]:
    """Minimal diagnostics for skills provider without leaking secrets."""
    repo = _repo(request)
    snap = repo.snapshot()
    csv_path_env = os.getenv("SKILLS_CSV_PATH")
    if csv_path_env:
        csv_path = Path(csv_path_env)
    else:
        csv_path = getattr(repo, "_csv_path", Path("/app/data/skills.csv"))
    notion_token = os.getenv("NOTION_API_KEY") or os.getenv("NOTION_SECRET")
    notion_db = os.getenv("NOTION_DB_SKILLS") or os.getenv("NOTION_DB")
    sample = []
    for s in (snap.skills[:2] if getattr(snap, "skills", None) else []):
        sample.append({"slug": getattr(s, "key", ""), "title_en": s.title_en[:60], "title_ru": s.title_ru[:60]})
    return {
        "provider": getattr(snap, "source", None) or "unknown",
        "csv_path": str(csv_path),
        "csv_exists": csv_path.exists(),
        "notion": {
            "token": "SET" if notion_token else "EMPTY",
            "db": "SET" if notion_db else "EMPTY",
            "ok": bool(getattr(snap, "notion", False)),
        },
        "count": len(getattr(snap, "skills", []) or []),
        "sample": sample,
    }


@api_router.get("/skills/{slug}")
def get_skill_api(
    slug: str,
    request: Request,
    lang: Optional[str] = Query(default=None, description="ru|en for projected payload"),
) -> Dict[str, Any]:
    return _get_skill_impl(slug=slug, request=request, lang=lang)


@api_router.get("/skills/search")
def search_skills_api(
    request: Request,
    q: str = Query(..., description="Search query"),
    lang: Optional[str] = Query(default=None, description="ru|en for projected payload"),
    limit: int = Query(default=10, ge=1, le=50, description="Max number of results"),
) -> List[Dict[str, Any]]:
    repo = _repo(request)
    lang_key = _lang_key(lang) if lang else "en"
    top_skills = repo.relevant_skills(q, top_k=limit)
    if lang:
        return [_project_card(skill, lang_key) for skill in top_skills]
    return [
        {
            "slug": skill.key,
            "title_en": skill.title("en"),
            "title_ru": skill.title("ru"),
            "short_en": skill.summary("en"),
            "short_ru": skill.summary("ru"),
            "tags": skill.tags,
        }
        for skill in top_skills
    ]


