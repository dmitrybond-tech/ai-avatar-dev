from __future__ import annotations

from typing import Any, Dict, List, Optional

import json
import logging
import os
import re
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/skills", tags=["skills"])


def _slugify_english(title_en: str) -> str:
    base = title_en.strip().lower()
    base = re.sub(r"[^a-z0-9\s\-]+", "", base)
    base = re.sub(r"[\s\-]+", "-", base).strip("-")
    return base or "untitled"


class Skill(BaseModel):
    slug: str
    title_en: str
    title_ru: str
    short_en: str
    short_ru: str
    icon: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class SkillDetail(Skill):
    bullets_en: List[str] = Field(default_factory=list)
    bullets_ru: List[str] = Field(default_factory=list)
    examples_en: List[str] = Field(default_factory=list)
    examples_ru: List[str] = Field(default_factory=list)


def _read_seed(lang: str) -> List[Dict[str, Any]]:
    here = os.path.dirname(os.path.dirname(__file__))  # apps/miniapp-api
    seed_path = os.path.join(here, "seed", f"skills.{lang}.json")
    if not os.path.exists(seed_path):
        return []
    try:
        with open(seed_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to read seed %s: %s", seed_path, e)
        return []


def _merge_seeds(en: List[Dict[str, Any]], ru: List[Dict[str, Any]]) -> List[SkillDetail]:
    ru_by_slug: Dict[str, Dict[str, Any]] = {item.get("slug") or _slugify_english(item.get("title_en", "")): item for item in ru}
    merged: List[SkillDetail] = []
    for e in en:
        slug = e.get("slug") or _slugify_english(e.get("title_en", ""))
        r = ru_by_slug.get(slug, {})
        merged.append(
            SkillDetail(
                slug=slug,
                title_en=e.get("title_en", ""),
                title_ru=r.get("title_ru") or e.get("title_ru") or e.get("title_en", ""),
                short_en=e.get("short_en", ""),
                short_ru=r.get("short_ru") or e.get("short_ru") or e.get("short_en", ""),
                icon=e.get("icon") or r.get("icon"),
                tags=e.get("tags") or r.get("tags") or [],
                bullets_en=e.get("bullets_en") or [],
                bullets_ru=r.get("bullets_ru") or e.get("bullets_ru") or [],
                examples_en=e.get("examples_en") or [],
                examples_ru=r.get("examples_ru") or e.get("examples_ru") or [],
            )
        )
    return merged


def _get_notion_client():
    try:
        from notion_client import Client  # type: ignore
    except Exception:
        return None
    api_key = os.getenv("NOTION_API_KEY") or os.getenv("NOTION_SECRET")
    if not api_key:
        return None
    return Client(auth=api_key, timeout=10)


def _fetch_from_notion() -> List[SkillDetail]:
    """Fetch skills from Notion; tolerate absence and return []."""
    c = _get_notion_client()
    if c is None:
        return []

    db_id = os.getenv("NOTION_DB_SKILLS") or os.getenv("NOTION_DB")
    if not db_id:
        return []

    # Build a permissive filter to accept legacy "Rules" context
    query: Dict[str, Any] = {
        "database_id": db_id,
        # Optional context filter
    }
    try:
        resp = c.databases.query(**query)
        pages = resp.get("results", [])
    except Exception as e:
        logger.warning("Notion query failed: %s", e)
        return []

    def _plain(rt: Dict[str, Any]) -> str:
        t = rt.get(rt.get("type", ""), [])
        if isinstance(t, list) and t:
            return "".join([x.get("plain_text", "") for x in t]).strip()
        return ""

    def _rich_to_lines(prop: Dict[str, Any]) -> List[str]:
        arr = prop.get(prop.get("type", ""), [])
        lines: List[str] = []
        for b in arr or []:
            txt = b.get("plain_text") or b.get("text", {}).get("content") or ""
            if txt:
                for line in re.split(r"[\r\n]+", txt):
                    cleaned = line.strip(" •-\t")
                    if cleaned:
                        lines.append(cleaned)
        return lines

    skills: List[SkillDetail] = []
    for p in pages:
        props: Dict[str, Any] = p.get("properties", {})
        title_en = _plain(props.get("Title EN", {})) or _plain(props.get("Name", {}))
        title_ru = _plain(props.get("Title RU", {})) or title_en
        short_en = _plain(props.get("Short EN", {})) or _plain(props.get("Summary", {}))
        short_ru = _plain(props.get("Short RU", {})) or short_en
        slug = _plain(props.get("Slug", {})) or _slugify_english(title_en)
        icon = None
        try:
            icon = (p.get("icon", {}) or {}).get("emoji")
        except Exception:
            pass
        tags_prop = props.get("Tags", {})
        tags_list: List[str] = []
        if tags_prop.get("type") == "multi_select":
            tags_list = [x.get("name", "") for x in tags_prop.get("multi_select", []) if x.get("name")]

        bullets_en = _rich_to_lines(props.get("Bullets EN", {})) or _rich_to_lines(props.get("Bullets", {}))
        bullets_ru = _rich_to_lines(props.get("Bullets RU", {}))
        examples_en = _rich_to_lines(props.get("Examples EN", {})) or _rich_to_lines(props.get("Examples", {}))
        examples_ru = _rich_to_lines(props.get("Examples RU", {}))

        skills.append(
            SkillDetail(
                slug=slug,
                title_en=title_en,
                title_ru=title_ru,
                short_en=short_en,
                short_ru=short_ru,
                icon=icon,
                tags=tags_list,
                bullets_en=bullets_en,
                bullets_ru=bullets_ru,
                examples_en=examples_en,
                examples_ru=examples_ru,
            )
        )

    # Deduplicate by slug (Notion takes precedence later when merged with seeds)
    seen: Dict[str, SkillDetail] = {}
    for s in skills:
        seen[s.slug] = s
    return list(seen.values())


def _load_skills() -> List[SkillDetail]:
    notion = _fetch_from_notion()
    seeds_en = _read_seed("en")
    seeds_ru = _read_seed("ru")
    seeds = _merge_seeds(seeds_en, seeds_ru)

    # Merge: Notion takes precedence over seeds
    by_slug: Dict[str, SkillDetail] = {s.slug: s for s in seeds}
    for s in notion:
        by_slug[s.slug] = s
    return list(by_slug.values())


def _project_lang(s: SkillDetail, lang: Optional[str]) -> Dict[str, Any]:
    if not lang:
        return s.model_dump()
    key = "ru" if lang.lower().startswith("ru") else "en"
    return {
        "slug": s.slug,
        "title": s.title_ru if key == "ru" else s.title_en,
        "short": s.short_ru if key == "ru" else s.short_en,
        "icon": s.icon,
        "tags": s.tags,
        "bullets": s.bullets_ru if key == "ru" else s.bullets_en,
        "examples": s.examples_ru if key == "ru" else s.examples_en,
    }


@router.get("")
def list_skills(lang: Optional[str] = Query(default=None, description="ru|en for projected payload")) -> List[Dict[str, Any]]:
    skills = _load_skills()
    if lang:
        return [
            {
                "slug": s.slug,
                "title": (s.title_ru if lang.startswith("ru") else s.title_en),
                "short": (s.short_ru if lang.startswith("ru") else s.short_en),
                "icon": s.icon,
                "tags": s.tags,
            }
            for s in skills
        ]
    return [s.model_dump() for s in skills]


@router.get("/{slug}")
def get_skill(slug: str, lang: Optional[str] = Query(default=None, description="ru|en for projected payload")) -> Dict[str, Any]:
    skills = _load_skills()
    found = next((s for s in skills if s.slug == slug), None)
    if not found:
        raise HTTPException(status_code=404, detail="Skill not found")
    return _project_lang(found, lang)


# Legacy aliases for /rules
alias_router = APIRouter(tags=["legacy-rules"]) 


@alias_router.get("/rules")
def rules_alias(lang: Optional[str] = Query(default=None)) -> List[Dict[str, Any]]:
    logger.warning("/rules is deprecated; use /skills instead")
    return list_skills(lang=lang)


@alias_router.get("/rules/{slug}")
def rules_detail_alias(slug: str, lang: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    logger.warning("/rules/{slug} is deprecated; use /skills/{slug} instead")
    return get_skill(slug=slug, lang=lang)


