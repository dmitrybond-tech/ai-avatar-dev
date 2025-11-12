from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from ..services.skills import SkillRecord, SkillsRepository
from ..services.skills_loader import get_loader
from ..services.skills_fallback import get_fallback_skills
from ..services.llm_grok import get_grok_client

logger = logging.getLogger(__name__)

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


def _load_skills_with_fallback() -> List[SkillRecord]:
    """Load skills from CSV with fallback to hardcoded skills if CSV fails."""
    source = os.getenv("SKILLS_SOURCE", "auto").strip().lower()
    if source == "csv":
        skills = get_loader().load_skills()
        if not skills:
            logger.warning("CSV loader returned 0 skills, using fallback")
            return get_fallback_skills()
        return skills
    # For non-CSV mode, use repository (which may use Notion or CSV)
    return []


def _list_skills_impl(request: Request, lang: Optional[str]) -> List[Dict[str, Any]]:
    source = os.getenv("SKILLS_SOURCE", "auto").strip().lower()
    if source == "csv":
        skills = _load_skills_with_fallback()
    else:
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
    source = os.getenv("SKILLS_SOURCE", "auto").strip().lower()
    if source == "csv":
        skills = _load_skills_with_fallback()
        skill = next((s for s in skills if s.key == slug), None)
    else:
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
    source = os.getenv("SKILLS_SOURCE", "auto").strip().lower()
    csv_path_env = os.getenv("SKILLS_CSV_PATH")
    if csv_path_env:
        csv_path = Path(csv_path_env)
    else:
        csv_path = Path("/app/data/skills.csv")
    
    errors: List[str] = []
    csv_ok = False
    
    if source == "csv":
        # Try to load CSV directly to check if it works
        try:
            loader = get_loader()
            csv_skills = loader.load_skills()
            csv_ok = len(csv_skills) > 0
            if not csv_ok:
                errors.append("CSV loaded but returned 0 skills")
        except Exception as exc:
            errors.append(f"CSV load failed: {str(exc)[:200]}")
            csv_ok = False
        
        # Load with fallback
        skills = _load_skills_with_fallback()
        actual_source = "fallback" if not csv_ok else "csv"
        
        sample = []
        for s in skills[:2]:
            sample.append({
                "slug": s.key,
                "title": s.title("en")[:60],
            })
        
        return {
            "source": actual_source,
            "count": len(skills),
            "csv_path": str(csv_path),
            "csv_exists": csv_path.exists(),
            "csv_ok": csv_ok,
            "errors": errors if errors else None,
            "sample": sample,
        }
    else:
        repo = _repo(request)
        snap = repo.snapshot()
        notion_token = os.getenv("NOTION_API_KEY") or os.getenv("NOTION_SECRET")
        notion_db = os.getenv("NOTION_DB_SKILLS") or os.getenv("NOTION_DB")
        
        # Check CSV status even in non-CSV mode
        try:
            loader = get_loader()
            csv_skills = loader.load_skills()
            csv_ok = len(csv_skills) > 0
        except Exception as exc:
            errors.append(f"CSV check failed: {str(exc)[:200]}")
            csv_ok = False
        
        sample = []
        for s in (snap.skills[:2] if getattr(snap, "skills", None) else []):
            sample.append({"slug": getattr(s, "key", ""), "title_en": s.title_en[:60], "title_ru": s.title_ru[:60]})
        
        return {
            "source": getattr(snap, "source", None) or "unknown",
            "count": len(getattr(snap, "skills", []) or []),
            "csv_path": str(csv_path),
            "csv_exists": csv_path.exists(),
            "csv_ok": csv_ok,
            "errors": errors if errors else None,
            "notion": {
                "token": "SET" if notion_token else "EMPTY",
                "db": "SET" if notion_db else "EMPTY",
                "ok": bool(getattr(snap, "notion", False)),
            },
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
    source = os.getenv("SKILLS_SOURCE", "auto").strip().lower()
    if source == "csv":
        skills = _load_skills_with_fallback()
        # Simple search using loader
        from ..services.skills_loader import get_loader
        lang_key = _lang_key(lang) if lang else "en"
        top_skills = get_loader().search_skills(q, lang=lang_key, top_k=limit)
    else:
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


# Request/Response models for /api/skills/ask
class AskRequest(BaseModel):
    q: str
    lang: Optional[str] = None
    selected: Optional[List[str]] = None


class AskResponse(BaseModel):
    answer: str
    used_skills: List[str]
    model: str
    tokens_estimate: int


@api_router.post("/skills/ask", response_model=AskResponse)
def ask_skills(request: Request, body: AskRequest) -> AskResponse:
    """Ask Grok about skills based on user question."""
    source = os.getenv("SKILLS_SOURCE", "auto").strip().lower()
    
    # Check if Grok is available
    grok_client = get_grok_client()
    if not grok_client.available:
        api_key_set = bool(os.getenv("XAI_API_KEY"))
        if not api_key_set:
            raise HTTPException(status_code=401, detail="XAI_API_KEY not configured")
        raise HTTPException(status_code=502, detail="Grok provider unavailable")

    # Load skills using the loader with fallback
    if source == "csv":
        skills = _load_skills_with_fallback()
    else:
        loader = get_loader()
        skills = loader.load_skills()
        if not skills:
            skills = get_fallback_skills()
    if not skills:
        raise HTTPException(status_code=503, detail="No skills available")

    # Determine language
    lang = body.lang or "en"
    lang_key = _lang_key(lang)

    # Find relevant skills
    query = body.q.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query 'q' cannot be empty")

    # Use selected skills if provided, otherwise search
    if body.selected:
        selected_skills = [s for s in skills if s.key in body.selected]
        if not selected_skills:
            # Fallback to search if selected not found
            if source == "csv":
                from ..services.skills_loader import get_loader
                selected_skills = get_loader().search_skills(query, lang=lang_key, top_k=5)
            else:
                repo = _repo(request)
                selected_skills = repo.relevant_skills(query, top_k=5)
    else:
        if source == "csv":
            from ..services.skills_loader import get_loader
            selected_skills = get_loader().search_skills(query, lang=lang_key, top_k=5)
        else:
            repo = _repo(request)
            selected_skills = repo.relevant_skills(query, top_k=5)

    if not selected_skills:
        selected_skills = skills[:3]  # Fallback to first 3 skills

    # Build skills context string
    context_parts = []
    for skill in selected_skills[:5]:  # Limit to top 5
        skill_info = [
            f"Skill: {skill.title(lang_key)}",
            f"Summary: {skill.summary(lang_key)}",
        ]
        if skill.tags:
            skill_info.append(f"Tags: {', '.join(skill.tags)}")
        if skill.bullets(lang_key):
            bullets_text = "; ".join(skill.bullets(lang_key)[:3])
            skill_info.append(f"Capabilities: {bullets_text}")
        if skill.examples(lang_key):
            examples_text = "; ".join(skill.examples(lang_key)[:2])
            skill_info.append(f"Examples: {examples_text}")
        context_parts.append("\n".join(skill_info))

    skills_context = "\n\n".join(context_parts)

    # Call Grok
    try:
        answer = grok_client.ask_with_context(
            user_question=query,
            skills_context=skills_context,
        )
        if not answer:
            raise HTTPException(status_code=502, detail="Grok provider returned empty response")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Grok API call failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail="Grok provider error; try again later")

    # Estimate tokens (rough: ~4 chars per token)
    tokens_estimate = len(query) + len(skills_context) + len(answer or "")
    tokens_estimate = tokens_estimate // 4

    return AskResponse(
        answer=answer or "No answer generated",
        used_skills=[s.key for s in selected_skills],
        model=grok_client._model,
        tokens_estimate=tokens_estimate,
    )


