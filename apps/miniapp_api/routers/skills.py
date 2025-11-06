from __future__ import annotations

from typing import Any, Dict, List, Optional

import json
import logging
import os
import re
from fastapi import APIRouter, HTTPException, Query


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/skills", tags=["skills"])


def _lang(v: Optional[str]) -> str:
    return "ru" if (v or "").lower().startswith("ru") else "en"


def _slugify_english(title_en: str) -> str:
    base = title_en.strip().lower()
    base = re.sub(r"[^a-z0-9\s\-]+", "", base)
    base = re.sub(r"[\s\-]+", "-", base).strip("-")
    return base or "untitled"


def _read_seed(lang: str) -> List[Dict[str, Any]]:
    # Try to reuse seeds from the dash package if present: apps/miniapp-api/seed
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    seed_path = os.path.join(repo_root, "miniapp-api", "seed", f"skills.{lang}.json")
    if not os.path.exists(seed_path):
        return []
    try:
        with open(seed_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to read seed %s: %s", seed_path, e)
        return []


def _get_notion_client():
    try:
        from notion_client import Client  # type: ignore
    except Exception:
        return None
    api_key = os.getenv("NOTION_API_KEY") or os.getenv("NOTION_SECRET")
    if not api_key:
        return None
    return Client(auth=api_key, timeout=10)


def _fetch_from_notion() -> List[Dict[str, Any]]:
    c = _get_notion_client()
    if c is None:
        return []

    db_id = os.getenv("NOTION_DB_SKILLS") or os.getenv("NOTION_DB")
    if not db_id:
        return []

    try:
        resp = c.databases.query(database_id=db_id)
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

    skills: List[Dict[str, Any]] = []
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
            {
                "slug": slug,
                "title_en": title_en,
                "title_ru": title_ru,
                "short_en": short_en,
                "short_ru": short_ru,
                "icon": icon,
                "tags": tags_list,
                "bullets_en": bullets_en,
                "bullets_ru": bullets_ru,
                "examples_en": examples_en,
                "examples_ru": examples_ru,
            }
        )

    # Deduplicate by slug (Notion takes precedence later when merged with seeds)
    by_slug: Dict[str, Dict[str, Any]] = {}
    for s in skills:
        by_slug[s["slug"]] = s
    return list(by_slug.values())


def load_skills(lang: str) -> List[Dict[str, Any]]:
    notion = _fetch_from_notion()
    seeds_en = _read_seed("en")
    seeds_ru = _read_seed("ru")

    # Merge RU onto EN by slug for seeds
    ru_by_slug: Dict[str, Dict[str, Any]] = {x.get("slug") or _slugify_english(x.get("title_en", "")): x for x in seeds_ru}
    merged_seeds: Dict[str, Dict[str, Any]] = {}
    for e in seeds_en:
        slug = e.get("slug") or _slugify_english(e.get("title_en", ""))
        r = ru_by_slug.get(slug, {})
        merged_seeds[slug] = {
            "slug": slug,
            "title_en": e.get("title_en", ""),
            "title_ru": r.get("title_ru") or e.get("title_ru") or e.get("title_en", ""),
            "short_en": e.get("short_en", ""),
            "short_ru": r.get("short_ru") or e.get("short_ru") or e.get("short_en", ""),
            "icon": e.get("icon") or r.get("icon"),
            "tags": e.get("tags") or r.get("tags") or [],
            "bullets_en": e.get("bullets_en") or [],
            "bullets_ru": r.get("bullets_ru") or e.get("bullets_ru") or [],
            "examples_en": e.get("examples_en") or [],
            "examples_ru": r.get("examples_ru") or e.get("examples_ru") or [],
        }

    # Notion takes precedence over seeds
    by_slug: Dict[str, Dict[str, Any]] = dict(merged_seeds)
    for s in notion:
        by_slug[s["slug"]] = s

    # Project to requested language
    key = "ru" if lang == "ru" else "en"
    projected: List[Dict[str, Any]] = []
    for s in by_slug.values():
        projected.append(
            {
                "slug": s["slug"],
                "title": s["title_ru"] if key == "ru" else s["title_en"],
                "short": s["short_ru"] if key == "ru" else s["short_en"],
                "icon": s.get("icon"),
                "tags": s.get("tags", []),
                "bullets": s.get("bullets_ru", []) if key == "ru" else s.get("bullets_en", []),
                "examples": s.get("examples_ru", []) if key == "ru" else s.get("examples_en", []),
            }
        )
    return sorted(projected, key=lambda x: x["slug"])


@router.get("")
def list_skills(lang: Optional[str] = Query(default=None)) -> List[Dict[str, Any]]:
    return load_skills(_lang(lang))


@router.get("/{slug}")
def get_skill(slug: str, lang: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    for s in load_skills(_lang(lang)):
        if s.get("slug") == slug:
            return s
    raise HTTPException(status_code=404, detail="Skill not found")


