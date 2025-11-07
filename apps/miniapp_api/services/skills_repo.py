"""Notion-backed repository for skills cards."""
from __future__ import annotations

import logging
import re
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from notion_client import Client
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class Skill(BaseModel):
    id: str
    slug: str
    title: str
    category: Optional[str] = None
    level: Optional[str] = None
    short: Optional[str] = None
    long: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    order: Optional[int] = None
    bullets: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)


def _plain(blocks: Optional[List[Dict[str, Any]]]) -> str:
    """Convert Notion rich_text/title blocks to plain text."""

    if not blocks:
        return ""
    chunks: List[str] = []
    for item in blocks:
        text = item.get("plain_text")
        if not text and isinstance(item.get("text"), dict):
            text = item["text"].get("content")
        if text:
            chunks.append(str(text))
    return "".join(chunks).strip()


def _slugify(value: str) -> str:
    base = value.strip().lower()
    base = re.sub(r"[^a-z0-9\s\-]+", "", base)
    base = re.sub(r"[\s\-]+", "-", base).strip("-")
    return base or "skill"


def _pick_locale(props: Dict[str, Any], base: str, lang: str) -> Optional[str]:
    """Select localized property value using tolerant naming."""

    lang = (lang or "en").lower()
    candidates = (
        f"{base} {lang.upper()}",
        f"{base}_{lang}",
        f"{base}{lang.upper()}",
        base,
    )
    for candidate in candidates:
        for prop_name, prop in props.items():
            if prop_name.lower() != candidate.lower():
                continue
            p_type = prop.get("type")
            if p_type in {"rich_text", "title"}:
                return _plain(prop.get(p_type, []))
            if p_type == "select" and prop.get("select"):
                return str(prop["select"].get("name", "")).strip() or None
            if p_type == "formula":
                formula = prop.get("formula") or {}
                for key in ("string", "number"):
                    if formula.get(key) not in (None, ""):
                        return str(formula[key]).strip()
            if "plain_text" in prop and prop["plain_text"]:
                return str(prop["plain_text"]).strip()
    return None


def _rich_to_lines(prop: Dict[str, Any]) -> List[str]:
    p_type = prop.get("type")
    blocks: Optional[List[Dict[str, Any]]] = None
    if p_type in {"rich_text", "title"}:
        blocks = prop.get(p_type)
    elif p_type == "paragraph":
        blocks = prop.get("paragraph")
    lines: List[str] = []
    if not blocks:
        return lines
    for block in blocks:
        raw = block.get("plain_text") or block.get("text", {}).get("content")
        if not raw:
            continue
        for segment in re.split(r"[\r\n]+", str(raw)):
            cleaned = segment.strip(" •-\t")
            if cleaned:
                lines.append(cleaned)
    return lines


def _resolve_rich_list(props: Dict[str, Any], base: str, lang: str) -> List[str]:
    lang = (lang or "en").lower()
    candidates = (
        f"{base} {lang.upper()}",
        f"{base}_{lang}",
        f"{base}{lang.upper()}",
        base,
    )
    for candidate in candidates:
        for prop_name, prop in props.items():
            if prop_name.lower() != candidate.lower():
                continue
            lines = _rich_to_lines(prop)
            if lines:
                return lines
    return []


class SkillsRepository:
    def __init__(self, client: Client, db_id: str, timeout: int = 10, cache_ttl: int = 90):
        self.client = client
        self.db_id = db_id
        self.timeout = timeout
        self.cache_ttl = max(60, min(cache_ttl, 120))

    def _query_all(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        start_cursor: Optional[str] = None
        while True:
            try:
                response = self.client.databases.query(
                    database_id=self.db_id,
                    start_cursor=start_cursor,
                    page_size=100,
                )
            except Exception:  # noqa: BLE001
                logger.exception("skills_notion_query_failed")
                raise
            results.extend(response.get("results", []))
            if not response.get("has_more"):
                break
            start_cursor = response.get("next_cursor")
            if not start_cursor:
                break
        return results

    def _resolve_tags(self, props: Dict[str, Any]) -> List[str]:
        for key in ("Tags", "Теги", "Labels"):
            prop = props.get(key)
            if not prop:
                continue
            if prop.get("type") == "multi_select":
                return [item.get("name", "").strip() for item in prop.get("multi_select", []) if item.get("name")]
        return []

    def _resolve_category(self, props: Dict[str, Any]) -> Optional[str]:
        for key in ("Category", "Domain", "Категория", "Домен"):
            prop = props.get(key)
            if not prop:
                continue
            p_type = prop.get("type")
            if p_type == "select" and prop.get("select"):
                return prop["select"].get("name")
            if p_type == "multi_select" and prop.get("multi_select"):
                names = [item.get("name", "") for item in prop["multi_select"] if item.get("name")]
                if names:
                    return ", ".join(names)
        return None

    def _resolve_level(self, props: Dict[str, Any]) -> Optional[str]:
        for key in ("Level", "Уровень"):
            prop = props.get(key)
            if not prop:
                continue
            if prop.get("type") == "select" and prop.get("select"):
                return prop["select"].get("name")
        return None

    def _resolve_number(self, props: Dict[str, Any], keys: Tuple[str, ...]) -> Optional[int]:
        for key in keys:
            prop = props.get(key)
            if not prop:
                continue
            if prop.get("type") == "number":
                value = prop.get("number")
                if value is None:
                    continue
                try:
                    return int(value)
                except (TypeError, ValueError):
                    continue
            if prop.get("type") == "formula":
                formula = prop.get("formula") or {}
                number = formula.get("number")
                if number is not None:
                    try:
                        return int(number)
                    except (TypeError, ValueError):
                        continue
        return None

    def _resolve_slug(self, props: Dict[str, Any], title: str, page_id: str) -> str:
        slug_candidates = ("Slug", "slug", "ID", "Key", "Alias")
        for candidate in slug_candidates:
            for prop_name, prop in props.items():
                if prop_name.lower() != candidate.lower():
                    continue
                p_type = prop.get("type")
                if p_type in {"rich_text", "title"}:
                    slug_value = _plain(prop.get(p_type, []))
                elif p_type == "select" and prop.get("select"):
                    slug_value = prop["select"].get("name", "")
                elif p_type == "formula":
                    formula = prop.get("formula") or {}
                    slug_value = formula.get("string") or formula.get("number") or ""
                else:
                    slug_value = prop.get("plain_text") or ""
                slug_value = str(slug_value or "").strip()
                if slug_value:
                    return _slugify(slug_value)
        fallback = _slugify(title)
        if fallback:
            return fallback
        return page_id.replace("-", "")

    def _map_page(self, page: Dict[str, Any], lang: str) -> Optional[Skill]:
        props = page.get("properties", {}) or {}
        lang = "ru" if (lang or "").lower().startswith("ru") else "en"

        title = (
            _pick_locale(props, "Title", lang)
            or _pick_locale(props, "Name", lang)
            or _plain(props.get("Name", {}).get("title", []))
            or _plain(props.get("Title", {}).get("title", []))
        )
        if not title:
            logger.debug("skills_skip_page_missing_title page_id=%s", page.get("id"))
            return None

        page_id = page.get("id", "")
        slug = self._resolve_slug(props, title, page_id)

        short = (
            _pick_locale(props, "Short", lang)
            or _pick_locale(props, "Summary", lang)
            or _pick_locale(props, "Description", lang)
        )
        long = _pick_locale(props, "Long", lang) or _pick_locale(props, "Details", lang)

        skill = Skill(
            id=page_id,
            slug=slug,
            title=title,
            category=self._resolve_category(props),
            level=self._resolve_level(props),
            short=short,
            long=long,
            tags=self._resolve_tags(props),
            order=self._resolve_number(props, ("Order", "Sort", "Index", "Порядок")),
            bullets=_resolve_rich_list(props, "Bullets", lang) or _resolve_rich_list(props, "Points", lang),
            examples=_resolve_rich_list(props, "Examples", lang) or _resolve_rich_list(props, "Use Cases", lang),
        )
        return skill

    def _fetch(self, lang: str) -> Tuple[List[Skill], Dict[str, Any]]:
        t0 = time.time()
        pages = self._query_all()
        items: List[Skill] = []

        for page in pages:
            try:
                skill = self._map_page(page, lang)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "skills_page_map_failed page_id=%s error=%s", page.get("id"), exc.__class__.__name__
                )
                continue
            if skill:
                items.append(skill)

        elapsed_ms = int((time.time() - t0) * 1000)
        meta = {
            "count": len(items),
            "elapsed_ms": elapsed_ms,
            "cache_ttl": self.cache_ttl,
        }
        logger.info("skills_fetch_completed lang=%s count=%s elapsed_ms=%s", lang, meta["count"], meta["elapsed_ms"])
        return items, meta

    def _cache_bucket(self) -> int:
        return int(time.time() // self.cache_ttl)

    @lru_cache(maxsize=8)
    def _get_skills_cached(self, lang: str, bucket: int) -> Tuple[List[Skill], Dict[str, Any]]:
        return self._fetch(lang)

    def get_skills(self, lang: str) -> Tuple[List[Skill], Dict[str, Any]]:
        bucket = self._cache_bucket()
        return self._get_skills_cached("ru" if (lang or "").lower().startswith("ru") else "en", bucket)



