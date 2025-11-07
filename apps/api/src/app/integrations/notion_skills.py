"""Integration helpers for Skills data stored in Notion."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Literal, Optional, Sequence

from notion_client import APIResponseError, Client

from app.core.logging import get_logger
from app.core.settings import settings

Lang = Literal["ru", "en"]

logger = get_logger(__name__)


class NotionConfigError(RuntimeError):
    """Raised when Notion configuration is missing."""


class NotionServiceError(RuntimeError):
    """Raised on Notion API failures."""


@dataclass(slots=True)
class SkillRecord:
    """Internal representation of a skill entry."""

    id: str
    slug: str
    name: str
    short: str
    long: str
    tags: List[str] = field(default_factory=list)
    category: Optional[str] = None
    icon: Optional[str] = None
    order: Optional[int] = None


_client: Optional[Client] = None


def _get_notion_client() -> Client:
    global _client
    if _client is None:
        if not settings.notion_api_key:
            raise NotionConfigError("NOTION_API_KEY is not configured")
        timeout_ms = max(int(settings.notion_timeout or 10), 1) * 1000
        _client = Client(auth=settings.notion_api_key, timeout_ms=timeout_ms)
    return _client


def _rich_text_content(prop: Dict[str, object]) -> str:
    if not prop:
        return ""
    prop_type = prop.get("type")
    if prop_type not in {"rich_text", "title"}:
        return ""
    chunks = prop.get(prop_type, [])  # type: ignore[arg-type]
    if not isinstance(chunks, list):
        return ""
    parts: List[str] = []
    for item in chunks:
        if not isinstance(item, dict):
            continue
        text = item.get("plain_text")
        if isinstance(text, str):
            parts.append(text)
    return "".join(parts).strip()


def _multi_select_names(prop: Dict[str, object]) -> List[str]:
    if not prop or prop.get("type") != "multi_select":
        return []
    value = prop.get("multi_select")
    if not isinstance(value, list):
        return []
    names: List[str] = []
    for item in value:
        if isinstance(item, dict):
            name = item.get("name")
            if isinstance(name, str) and name.strip():
                names.append(name.strip())
    return names


def _select_name(prop: Dict[str, object]) -> Optional[str]:
    if not prop or prop.get("type") != "select":
        return None
    select = prop.get("select")
    if isinstance(select, dict):
        name = select.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


def _number_value(prop: Dict[str, object]) -> Optional[int]:
    if not prop or prop.get("type") != "number":
        return None
    value = prop.get("number")
    if isinstance(value, (int, float)):
        return int(value)
    return None


def _icon_value(page: Dict[str, object]) -> Optional[str]:
    icon = page.get("icon")
    if not isinstance(icon, dict):
        return None
    icon_type = icon.get("type")
    if icon_type == "emoji":
        emoji = icon.get("emoji")
        return emoji if isinstance(emoji, str) else None
    if icon_type == "external":
        external = icon.get("external")
        if isinstance(external, dict):
            url = external.get("url")
            if isinstance(url, str) and url.strip():
                return url
    if icon_type == "file":
        file_data = icon.get("file")
        if isinstance(file_data, dict):
            url = file_data.get("url")
            if isinstance(url, str) and url.strip():
                return url
    return None


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower())
    cleaned = normalized.strip("-")
    return cleaned or ""


def _extract_property(props: Dict[str, Dict[str, object]], candidates: Sequence[str]) -> Optional[Dict[str, object]]:
    for name in candidates:
        prop = props.get(name)
        if isinstance(prop, dict):
            return prop
    return None


def _resolve_lang_text(
    props: Dict[str, Dict[str, object]],
    lang: Lang,
    primary: Dict[Lang, Sequence[str]],
    secondary: Dict[Lang, Sequence[str]],
    shared: Sequence[str],
) -> str:
    candidates_sets: List[Sequence[str]] = [primary.get(lang, ())]
    candidates_sets.append(shared)
    other_lang: Lang = "ru" if lang == "en" else "en"
    candidates_sets.append(secondary.get(other_lang, ()))

    for candidates in candidates_sets:
        prop = _extract_property(props, candidates)
        if prop:
            value = _rich_text_content(prop)
            if value:
                return value
    return ""


def _resolve_tags(props: Dict[str, Dict[str, object]], lang: Lang) -> List[str]:
    lang_specific = _extract_property(
        props,
        ("EN:Tags", "Tags EN", "Tags (EN)") if lang == "en" else ("RU:Tags", "Tags RU", "Tags (RU)"),
    )
    if lang_specific:
        tags = _multi_select_names(lang_specific)
        if tags:
            return tags

    other_lang = "ru" if lang == "en" else "en"
    alt_specific = _extract_property(
        props,
        ("EN:Tags", "Tags EN", "Tags (EN)") if other_lang == "en" else ("RU:Tags", "Tags RU", "Tags (RU)"),
    )
    if alt_specific:
        tags = _multi_select_names(alt_specific)
        if tags:
            return tags

    shared = _extract_property(props, ("Tags", "Skill Tags"))
    if shared:
        return _multi_select_names(shared)

    return []


def _extract_slug(props: Dict[str, Dict[str, object]], fallback: str) -> str:
    slug_prop = _extract_property(props, ("Slug", "slug", "URL", "Link"))
    candidate = ""
    if slug_prop:
        prop_type = slug_prop.get("type")
        if prop_type == "rich_text":
            candidate = _rich_text_content(slug_prop)
        elif prop_type == "formula":
            formula = slug_prop.get("formula")
            if isinstance(formula, dict) and formula.get("type") == "string":
                value = formula.get("string")
                if isinstance(value, str):
                    candidate = value.strip()
        elif prop_type == "title":
            candidate = _rich_text_content(slug_prop)
    candidate = candidate.strip()
    slug = _slugify(candidate) if candidate else ""
    if slug:
        return slug
    fallback_slug = _slugify(fallback)
    return fallback_slug or fallback


def _page_to_skill(page: Dict[str, object], lang: Lang) -> Optional[SkillRecord]:
    props = page.get("properties")
    if not isinstance(props, dict):
        return None

    title_prop = _extract_property(props, ("Name", "Title"))
    name = _rich_text_content(title_prop or {})
    if not name:
        return None

    publish_prop = _extract_property(props, ("Publish", "Published", "Visible"))
    if not publish_prop or publish_prop.get("type") != "checkbox":
        return None
    if publish_prop.get("checkbox") is not True:
        return None

    short = _resolve_lang_text(
        props,
        lang,
        {
            "en": ("EN:Short", "Short EN", "Short (EN)"),
            "ru": ("RU:Short", "Short RU", "Short (RU)"),
        },
        {
            "en": ("RU:Short", "Short RU", "Short (RU)"),
            "ru": ("EN:Short", "Short EN", "Short (EN)"),
        },
        ("Short", "Summary", "Описание"),
    )
    if not short:
        # Fallback to name if short missing
        short = name

    long_text = _resolve_lang_text(
        props,
        lang,
        {
            "en": ("EN:Long", "Long EN", "Details EN"),
            "ru": ("RU:Long", "Long RU", "Details RU"),
        },
        {
            "en": ("RU:Long", "Long RU", "Details RU"),
            "ru": ("EN:Long", "Long EN", "Details EN"),
        },
        ("Long", "Details", "Описание"),
    )

    if not long_text:
        long_text = short

    tags = _resolve_tags(props, lang)

    category = _select_name(_extract_property(props, ("Category", "Group")) or {})
    order = _number_value(_extract_property(props, ("Order", "Sort", "Position")) or {})

    slug = _extract_slug(props, name)

    icon = _icon_value(page)

    return SkillRecord(
        id=str(page.get("id")),
        slug=slug,
        name=name,
        short=short,
        long=long_text,
        tags=tags,
        category=category,
        icon=icon,
        order=order,
    )


def fetch_skills(lang: Lang) -> List[SkillRecord]:
    if lang not in {"ru", "en"}:
        lang = "en"

    db_id = settings.notion_skills_db_id
    if not db_id:
        raise NotionConfigError("NOTION_DB_SKILLS is not configured")

    client = _get_notion_client()

    try:
        start_cursor: Optional[str] = None
        items: List[SkillRecord] = []
        while True:
            payload: Dict[str, object] = {
                "database_id": db_id,
                "filter": {
                    "property": "Publish",
                    "checkbox": {"equals": True},
                },
                "sorts": [
                    {"property": "Order", "direction": "ascending"},
                    {"property": "Name", "direction": "ascending"},
                ],
                "page_size": 100,
            }
            if start_cursor:
                payload["start_cursor"] = start_cursor

            response = client.databases.query(**payload)
            pages = response.get("results", [])
            if isinstance(pages, Iterable):
                for page in pages:
                    if isinstance(page, dict):
                        skill = _page_to_skill(page, lang)
                        if skill is not None:
                            items.append(skill)

            if not response.get("has_more"):
                break
            next_cursor = response.get("next_cursor")
            if isinstance(next_cursor, str) and next_cursor:
                start_cursor = next_cursor
            else:
                break

        # Final sort to ensure deterministic order when Order is missing
        items.sort(key=lambda item: ((item.order is None), item.order or 0, item.name.lower()))
        return items

    except APIResponseError as exc:  # pragma: no cover - network failure path
        logger.error(
            "Notion API error while querying skills: %s - %s (request_id=%s)",
            exc.code,
            exc.message,
            exc.request_id,
        )
        raise NotionServiceError(f"Notion API error: {exc.message}") from exc
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Unhandled Notion error while querying skills: %s", exc, exc_info=True)
        raise NotionServiceError("Failed to query Notion skills database") from exc


def fetch_skill_by_slug(slug: str, lang: Lang) -> Optional[SkillRecord]:
    slug_normalized = slug.strip().lower()
    if not slug_normalized:
        return None
    skills = fetch_skills(lang)
    for skill in skills:
        if skill.slug.lower() == slug_normalized:
            return skill
    return None



