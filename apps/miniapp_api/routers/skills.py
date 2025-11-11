from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from apps.miniapp_api.services.skills_service import SkillsRepository

router = APIRouter(tags=["skills"])
api_router = APIRouter(prefix="/api", tags=["skills"])
alias_router = APIRouter(tags=["legacy-rules"])


def _repo(request: Request) -> SkillsRepository:
    repo = getattr(request.app.state, "skills_repo", None)
    if repo is None:
        raise RuntimeError("skills repository not initialized")
    return repo


def _lang_key(lang: Optional[str]) -> str:
    if not lang:
        return "en"
    return "ru" if lang.lower().startswith("ru") else "en"


def _project_card(skill, lang: str) -> Dict[str, Any]:
    return {
        "slug": skill.key,
        "title": skill.title(lang),
        "short": skill.summary(lang),
        "tags": skill.tags,
    }


def _project_detail(skill, lang: str) -> Dict[str, Any]:
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


def _get_skill_impl(slug: str, request: Request, lang: Optional[str]) -> Dict[str, Any]:
    repo = _repo(request)
    snapshot = repo.snapshot()
    skill = next((item for item in snapshot.skills if item.key == slug), None)
    if not skill:
        raise HTTPException(status_code=404, detail="skill_not_found")
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
def list_skills(request: Request, lang: Optional[str] = Query(default=None)) -> List[Dict[str, Any]]:
    return _list_skills_impl(request=request, lang=lang)


@router.get("/skills/{slug}")
def get_skill(slug: str, request: Request, lang: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    return _get_skill_impl(slug=slug, request=request, lang=lang)


@alias_router.get("/rules")
def rules_alias(request: Request, lang: Optional[str] = Query(default=None)) -> List[Dict[str, Any]]:
    return _list_skills_impl(request=request, lang=lang)


@alias_router.get("/rules/{slug}")
def rules_detail_alias(slug: str, request: Request, lang: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    return _get_skill_impl(slug=slug, request=request, lang=lang)


@api_router.get("/skills")
def list_skills_api(request: Request, lang: Optional[str] = Query(default=None)) -> List[Dict[str, Any]]:
    return _list_skills_impl(request=request, lang=lang)


@api_router.get("/skills/{slug}")
def get_skill_api(slug: str, request: Request, lang: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    return _get_skill_impl(slug=slug, request=request, lang=lang)

