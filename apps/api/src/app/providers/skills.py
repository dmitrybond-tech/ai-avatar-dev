"""Skills data provider with Notion primary source and CSV fallback."""
from __future__ import annotations

import csv
import re
import time
import unicodedata
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Dict, Iterable, List, Literal, Optional, Sequence, Tuple

from notion_client import APIResponseError, Client
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.logging import get_logger
from app.core.settings import settings

Lang = Literal["en", "ru"]


logger = get_logger(__name__)


class SkillsSourceMode(str, Enum):
    """Available skills sources."""

    AUTO = "auto"
    NOTION = "notion"
    CSV = "csv"


class SkillsSourceError(RuntimeError):
    """Base class for skills source failures."""


class SkillsConfigurationError(SkillsSourceError):
    """Raised when mandatory configuration is missing."""


class SkillsUnavailableError(SkillsSourceError):
    """Raised when the configured source cannot provide data."""


class SkillsNotionError(SkillsUnavailableError):
    """Raised when the Notion source fails."""


class SkillsCsvError(SkillsUnavailableError):
    """Raised when the CSV fallback fails."""


@dataclass(slots=True)
class _FetchMeta:
    source: str = "unknown"
    fallback: bool = False
    count: int = 0
    lang: Lang = "en"


class SkillOut(BaseModel):
    """Public skill representation returned by the API."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    slug: str
    title: str
    short: str
    bullets: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    order: Optional[int] = None

    @field_validator("title", "short", mode="before")
    @classmethod
    def _strip_text(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @field_validator("bullets", "examples", "tags", mode="before")
    @classmethod
    def _ensure_list(cls, value: object) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, (tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            items = [part.strip() for part in value.split("\n")]
            return [item for item in items if item]
        return [str(value).strip()]


_last_fetch_meta = _FetchMeta()
_notion_client: Optional[Client] = None
_skills_cache: Dict[Lang, Tuple[float, List["SkillOut"]]] = {}
_cache_lock = Lock()


_TITLE_ALIASES: Dict[Lang, Tuple[str, ...]] = {
    "en": ("Title EN", "TitleEn", "Title_EN", "Title", "Name"),
    "ru": ("Title RU", "TitleRu", "Title_RU", "Title", "Name"),
}
_SHORT_ALIASES: Dict[Lang, Tuple[str, ...]] = {
    "en": ("Short EN", "ShortEn", "Short_EN", "Short"),
    "ru": ("Short RU", "ShortRu", "Short_RU", "Short"),
}
_BULLETS_ALIASES: Dict[Lang, Tuple[str, ...]] = {
    "en": ("Bullets EN", "BulletsEn", "Bullets_EN", "Bullets"),
    "ru": ("Bullets RU", "BulletsRu", "Bullets_RU", "Bullets"),
}
_EXAMPLES_ALIASES: Dict[Lang, Tuple[str, ...]] = {
    "en": ("Examples EN", "ExamplesEn", "Examples_EN", "Examples"),
    "ru": ("Examples RU", "ExamplesRu", "Examples_RU", "Examples"),
}

_TAGS_CANDIDATES = ("Tags", "Tag", "Skills", "Labels")
_ORDER_CANDIDATES = ("Order", "Priority", "Sort")
_SLUG_CANDIDATES = ("Slug", "Key", "Code")
_PUBLISH_FIELDS = ("Publish", "publish", "Published")
_PUBLISH_TRUE = {"true", "yes", "publish", "published", "public", "ready", "on", "enabled", "1"}
_PUBLISH_FALSE = {"false", "no", "draft", "off", "0", "disabled"}

_CYRILLIC_TRANSLIT = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "i",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def log_skills_source_configuration() -> None:
    """Log skills configuration at startup without leaking secrets."""

    source = _resolve_source_mode()
    notion_key_len = len(settings.notion_api_key or "")
    db_id_present = bool(settings.notion_skills_db_id)
    csv_path = _resolve_csv_path()
    logger.info(
        "skills_source_init mode=%s notion_api_key_len=%d notion_db_configured=%s csv_path=%s",
        source.value,
        notion_key_len,
        db_id_present,
        csv_path,
    )


def get_last_fetch_meta() -> _FetchMeta:
    """Return metadata about the most recent fetch."""

    return _last_fetch_meta


def get_skills(lang: Lang = "en") -> List[SkillOut]:
    """Fetch skills using the configured source with graceful fallback."""

    normalized_lang: Lang = "ru" if str(lang).strip().lower() == "ru" else "en"

    ttl = _resolve_cache_ttl()
    now = time.time()
    with _cache_lock:
        cached = _skills_cache.get(normalized_lang)
        if cached:
            cached_at, cached_items = cached
            if now - cached_at < ttl:
                logger.debug(
                    "skills_cache_hit lang=%s age=%.2fs ttl=%ss",
                    normalized_lang,
                    now - cached_at,
                    ttl,
                )
                return cached_items

    source_mode = _resolve_source_mode()

    skills: List[SkillOut]

    if source_mode is SkillsSourceMode.CSV:
        skills = _load_from_csv(normalized_lang)
        _store_fetch_meta("csv", False, len(skills), normalized_lang)
        logger.info(
            "skills_source=csv path=%s lang=%s count=%d",
            _resolve_csv_path(),
            normalized_lang,
            len(skills),
        )
    elif source_mode is SkillsSourceMode.NOTION:
        try:
            skills = _load_from_notion(normalized_lang)
            _store_fetch_meta("notion", False, len(skills), normalized_lang)
        except SkillsNotionError as exc:  # pragma: no cover - configuration/network
            _store_fetch_meta("notion", False, 0, normalized_lang)
            logger.warning(
                "skills_source=notion lang=%s count=0 error=%s",
                normalized_lang,
                exc,
            )
            raise
        except SkillsSourceError as exc:  # pragma: no cover - defensive
            _store_fetch_meta("notion", False, 0, normalized_lang)
            logger.warning(
                "skills_source=notion lang=%s count=0 error=%s",
                normalized_lang,
                exc,
            )
            raise SkillsUnavailableError(str(exc)) from exc
    else:
        try:
            skills = _load_from_notion(normalized_lang)
            _store_fetch_meta("notion", False, len(skills), normalized_lang)
        except SkillsNotionError as exc:
            csv_path = _resolve_csv_path()
            try:
                skills = _load_from_csv(normalized_lang)
            except SkillsCsvError:
                _store_fetch_meta("notion", False, 0, normalized_lang)
                logger.warning(
                    "skills_source=fallback_csv_failed path=%s lang=%s reason=%s",
                    csv_path,
                    normalized_lang,
                    exc,
                )
                raise
            logger.warning(
                "skills_source=fallback_csv path=%s lang=%s count=%d reason=%s",
                csv_path,
                normalized_lang,
                len(skills),
                exc,
            )
            _store_fetch_meta("csv", True, len(skills), normalized_lang)

    with _cache_lock:
        _skills_cache[normalized_lang] = (time.time(), skills)

    return skills


def _store_fetch_meta(source: str, fallback: bool, count: int, lang: Lang) -> None:
    global _last_fetch_meta
    _last_fetch_meta = _FetchMeta(source=source, fallback=fallback, count=count, lang=lang)


def _resolve_cache_ttl() -> int:
    """Return configured cache TTL in seconds within sane bounds."""

    raw_value = getattr(settings, "notion_cache_ttl_skills", 300)
    try:
        ttl = int(raw_value)
    except (TypeError, ValueError):
        ttl = 300
    if ttl < 60:
        return 60
    if ttl > 3600:
        return 3600
    return ttl


def _resolve_source_mode() -> SkillsSourceMode:
    raw = (settings.skills_source or "auto").strip().lower()
    try:
        return SkillsSourceMode(raw)
    except ValueError:
        logger.warning("skills_source_invalid value=%s defaulting=auto", raw)
        return SkillsSourceMode.AUTO


def _resolve_csv_path() -> Path:
    configured = (settings.skills_csv_path or "").strip()
    base_api_dir = Path(__file__).resolve().parents[3]
    if configured:
        candidate = Path(configured)
        if not candidate.is_absolute():
            if candidate.parts and candidate.parts[0] == "apps" and len(base_api_dir.parents) >= 2:
                project_root = base_api_dir.parents[1]
                candidate = (project_root / candidate).resolve()
            else:
                candidate = (base_api_dir / candidate).resolve()
    else:
        candidate = (base_api_dir / "data" / "skills.csv").resolve()
    return candidate


def _load_from_csv(lang: Lang) -> List[SkillOut]:
    path = _resolve_csv_path()
    if not path.exists():
        raise SkillsCsvError(f"CSV file not found: {path}")

    items: List[SkillOut] = []
    try:
        handle = path.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:  # pragma: no cover - filesystem specific
        raise SkillsCsvError(f"CSV file not readable: {path}") from exc

    with handle:
        reader = csv.DictReader(handle)
        try:
            rows = list(reader)
        except csv.Error as exc:  # pragma: no cover - malformed csv
            raise SkillsCsvError(f"CSV parse failed: {path}") from exc
        for index, row in enumerate(rows, start=1):
            title_key = f"Title {'EN' if lang == 'en' else 'RU'}"
            short_key = f"Short {'EN' if lang == 'en' else 'RU'}"
            bullets_key = f"Bullets {'EN' if lang == 'en' else 'RU'}"
            examples_key = f"Examples {'EN' if lang == 'en' else 'RU'}"

            title = (row.get(title_key) or row.get("Title") or "").strip()
            if not title:
                logger.warning(
                    "skills_source=csv lang=%s row=%d missing_title key=%s",
                    lang,
                    index,
                    title_key,
                )
                continue

            short = (row.get(short_key) or row.get("Short") or title).strip()

            bullets = _split_lines(row.get(bullets_key) or row.get("Bullets") or "")
            examples = _split_lines(row.get(examples_key) or row.get("Examples") or "")

            slug_raw = (row.get("Slug") or "").strip()
            slug = _slugify(slug_raw or title)

            tags_raw = row.get("Tags") or ""
            tags = _split_tags(tags_raw)

            order_value = row.get("Order")
            try:
                order = int(order_value) if order_value else index
            except (TypeError, ValueError):
                order = index

            try:
                skill = SkillOut(
                    id=row.get("ID", slug) or slug,
                    slug=slug,
                    title=title,
                    short=short,
                    bullets=bullets,
                    examples=examples,
                    tags=tags,
                    order=order,
                )
            except Exception as exc:  # pragma: no cover - defensive parse guard
                logger.warning(
                    "skills_source=csv lang=%s row=%d invalid_record error=%s",
                    lang,
                    index,
                    exc,
                )
                continue
            items.append(skill)

    unique = _ensure_unique_slugs(items)
    return _sort_skills(unique)


def _get_notion_client() -> Client:
    global _notion_client
    if _notion_client is not None:
        return _notion_client

    api_key = (settings.notion_api_key or "").strip()
    if not api_key:
        raise SkillsConfigurationError("NOTION_API_KEY is not configured")

    timeout_seconds = max(int(settings.notion_timeout or 10), 1)
    _notion_client = Client(auth=api_key, timeout_ms=timeout_seconds * 1000)
    return _notion_client


def _load_from_notion(lang: Lang) -> List[SkillOut]:
    database_id = (settings.notion_skills_db_id or "").strip()
    if not database_id:
        raise SkillsConfigurationError("NOTION_DB_SKILLS is not configured")

    client = _get_notion_client()

    try:
        items: List[SkillOut] = []
        start_cursor: Optional[str] = None
        index = 0
        while True:
            query: Dict[str, object] = {
                "database_id": database_id,
                "page_size": 100,
            }
            if start_cursor:
                query["start_cursor"] = start_cursor

            response = client.databases.query(**query)
            pages = response.get("results", [])
            if isinstance(pages, Iterable):
                for page in pages:
                    if not isinstance(page, dict):
                        continue
                    if not _is_published(page):
                        continue
                    index += 1
                    skill = _notion_page_to_skill(page, lang, index)
                    items.append(skill)

            if not response.get("has_more"):
                break
            next_cursor = response.get("next_cursor")
            if isinstance(next_cursor, str) and next_cursor:
                start_cursor = next_cursor
            else:
                break

        unique = _ensure_unique_slugs(items)
        sorted_items = _sort_skills(unique)
        logger.info("skills_source=notion lang=%s count=%d", lang, len(sorted_items))
        return sorted_items
    except APIResponseError as exc:  # pragma: no cover - network path
        logger.error(
            "skills_source=notion error=%s message=%s request_id=%s",
            exc.code,
            exc.message,
            getattr(exc, "request_id", ""),
        )
        raise SkillsNotionError(f"Notion API error: {exc.message}") from exc
    except SkillsSourceError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("skills_source=notion error=%s", exc, exc_info=True)
        raise SkillsNotionError("Failed to fetch skills from Notion") from exc


def _is_published(page: Dict[str, object]) -> bool:
    props = page.get("properties")
    if not isinstance(props, dict):
        return True

    publish_decisions: List[bool] = []

    for field in _PUBLISH_FIELDS:
        prop = _get_prop_case_insensitive(props, field)
        if not isinstance(prop, dict):
            continue
        value = _publish_property_truthy(prop)
        if value is not None:
            publish_decisions.append(value)

    status_prop = _get_prop_case_insensitive(props, "Status")
    if isinstance(status_prop, dict):
        status_value = _publish_property_truthy(status_prop)
        if status_value is not None:
            publish_decisions.append(status_value)

    if not publish_decisions:
        return True
    return any(publish_decisions)


def _publish_property_truthy(prop: Dict[str, object]) -> Optional[bool]:
    prop_type = prop.get("type")
    if prop_type == "checkbox":
        checkbox = prop.get("checkbox")
        if isinstance(checkbox, bool):
            return checkbox
        if checkbox is not None:
            return bool(checkbox)
        return None

    if prop_type == "select":
        select = prop.get("select")
        if isinstance(select, dict):
            name = select.get("name")
            if isinstance(name, str):
                return _coerce_bool(name)
        return None

    if prop_type == "status":
        status = prop.get("status")
        if isinstance(status, dict):
            name = status.get("name")
            if isinstance(name, str):
                return _coerce_bool(name)
        return None

    if prop_type == "formula":
        formula = prop.get("formula")
        if isinstance(formula, dict):
            formula_type = formula.get("type")
            if formula_type == "boolean":
                boolean_value = formula.get("boolean")
                if isinstance(boolean_value, bool):
                    return boolean_value
                if boolean_value is not None:
                    return bool(boolean_value)
            if formula_type == "number":
                number_value = formula.get("number")
                if isinstance(number_value, (int, float)):
                    return number_value != 0
            if formula_type == "string":
                string_value = formula.get("string")
                if isinstance(string_value, str):
                    return _coerce_bool(string_value)
        return None

    if prop_type in {"rich_text", "title"}:
        text = _rich_text(prop)
        if text:
            return _coerce_bool(text)

    return None


def _coerce_bool(value: str) -> Optional[bool]:
    lowered = value.strip().lower()
    if not lowered:
        return None
    if lowered in _PUBLISH_TRUE:
        return True
    if lowered in _PUBLISH_FALSE:
        return False
    return None


def _notion_page_to_skill(page: Dict[str, object], lang: Lang, index: int) -> SkillOut:
    props = page.get("properties")
    if not isinstance(props, dict):
        raise SkillsSourceError("Notion page is missing properties")

    page_id = str(page.get("id") or "")

    fallback_lang: Lang = "ru" if lang == "en" else "en"

    title_candidates = list(_TITLE_ALIASES.get(lang, ()))
    fallback_title_candidates = list(_TITLE_ALIASES.get(fallback_lang, ())) + ["Title", "Name"]

    title = _first_text(props, title_candidates)
    if not title:
        title = _first_text(props, fallback_title_candidates)
    if not title:
        raise SkillsSourceError(f"Missing required title for Notion page {page_id or 'unknown'}")

    slug = _extract_slug(props, title)

    short_candidates = list(_SHORT_ALIASES.get(lang, ()))
    fallback_short_candidates = list(_SHORT_ALIASES.get(fallback_lang, ())) + ["Short", "Summary", "Description"]

    short_value = _first_text(props, short_candidates)
    if not short_value:
        short_value = _first_text(props, fallback_short_candidates)
    short = short_value or title

    bullets_candidates = list(_BULLETS_ALIASES.get(lang, ()))
    fallback_bullets_candidates = list(_BULLETS_ALIASES.get(fallback_lang, ())) + ["Bullets", "Points", "List"]
    bullets = _first_lines(props, bullets_candidates) or _first_lines(props, fallback_bullets_candidates)

    examples_candidates = list(_EXAMPLES_ALIASES.get(lang, ()))
    fallback_examples_candidates = list(_EXAMPLES_ALIASES.get(fallback_lang, ())) + ["Examples", "Use Cases"]
    examples = _first_lines(props, examples_candidates) or _first_lines(props, fallback_examples_candidates)

    tags = _extract_tags(props)
    order = _extract_order(props)

    return SkillOut(
        id=page_id or slug,
        slug=slug,
        title=title,
        short=short,
        bullets=bullets,
        examples=examples,
        tags=tags,
        order=order if order is not None else index,
    )


def _get_prop_case_insensitive(
    props: Dict[str, Dict[str, object]], name: str
) -> Optional[Dict[str, object]]:
    """Return a property dict using case-insensitive lookup."""

    if not isinstance(props, dict):
        return None
    lowered = name.lower()
    for prop_name, prop_value in props.items():
        if isinstance(prop_value, dict) and prop_name.lower() == lowered:
            return prop_value
    return None


def _first_text(props: Dict[str, Dict[str, object]], candidates: Sequence[str]) -> str:
    """Return the first non-empty text value for the provided property names."""

    for name in candidates:
        prop = _get_prop_case_insensitive(props, name)
        value = _rich_text(prop)
        if value:
            return value
    return ""


def _prop_to_lines(prop: Optional[Dict[str, object]]) -> List[str]:
    """Convert a Notion property to an array of cleaned lines."""

    if not prop or not isinstance(prop, dict):
        return []
    prop_type = prop.get("type")
    segments: List[str] = []
    if prop_type in {"rich_text", "title"}:
        chunks = prop.get(prop_type)
        if isinstance(chunks, list):
            for chunk in chunks:
                if not isinstance(chunk, dict):
                    continue
                text = chunk.get("plain_text")
                if isinstance(text, str):
                    segments.extend(_split_lines(text))
                    continue
                text_data = chunk.get("text")
                if isinstance(text_data, dict):
                    content = text_data.get("content")
                    if isinstance(content, str):
                        segments.extend(_split_lines(content))
        else:
            segments.extend(_split_lines(_rich_text(prop)))
    else:
        segments.extend(_split_lines(_rich_text(prop)))
    return _dedupe_preserve(segments)


def _first_lines(props: Dict[str, Dict[str, object]], candidates: Sequence[str]) -> List[str]:
    """Return the first non-empty list of lines for the provided property names."""

    for name in candidates:
        prop = _get_prop_case_insensitive(props, name)
        lines = _prop_to_lines(prop)
        if lines:
            return lines
    return []


def _extract_slug(props: Dict[str, Dict[str, object]], title: str) -> str:
    for name in _SLUG_CANDIDATES:
        prop = props.get(name)
        if not isinstance(prop, dict):
            continue
        value = _rich_text(prop)
        if not value and prop.get("type") == "formula":
            formula = prop.get("formula")
            if isinstance(formula, dict):
                if formula.get("type") == "string":
                    candidate = formula.get("string")
                    if isinstance(candidate, str):
                        value = candidate.strip()
        if value:
            slug = _slugify(value)
            if slug:
                return slug
    return _slugify(title) or title


def _extract_tags(props: Dict[str, Dict[str, object]]) -> List[str]:
    for name in _TAGS_CANDIDATES:
        prop = props.get(name)
        if not isinstance(prop, dict):
            continue
        prop_type = prop.get("type")
        if prop_type == "multi_select":
            multi = prop.get("multi_select")
            if isinstance(multi, list):
                tags = [item.get("name", "") for item in multi if isinstance(item, dict)]
                return _dedupe_preserve([str(tag).strip() for tag in tags if str(tag).strip()])
        if prop_type in {"rich_text", "title"}:
            text = _rich_text(prop)
            if text:
                return _split_tags(text)
    return []


def _extract_order(props: Dict[str, Dict[str, object]]) -> Optional[int]:
    for name in _ORDER_CANDIDATES:
        prop = props.get(name)
        if not isinstance(prop, dict):
            continue
        prop_type = prop.get("type")
        if prop_type == "number":
            number = prop.get("number")
            if isinstance(number, (int, float)):
                return int(number)
        if prop_type in {"rich_text", "title"}:
            text = _rich_text(prop)
            if text and text.isdigit():
                return int(text)
        if prop_type == "formula":
            formula = prop.get("formula")
            if isinstance(formula, dict):
                if formula.get("type") == "number":
                    number = formula.get("number")
                    if isinstance(number, (int, float)):
                        return int(number)
                if formula.get("type") == "string":
                    text = formula.get("string")
                    if isinstance(text, str) and text.isdigit():
                        return int(text)
    return None


def _rich_text(prop: Optional[Dict[str, object]]) -> str:
    if not prop or not isinstance(prop, dict):
        return ""
    prop_type = prop.get("type")
    if prop_type in {"rich_text", "title"}:
        chunks = prop.get(prop_type)
        if not isinstance(chunks, list):
            return ""
        parts: List[str] = []
        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue
            text = chunk.get("plain_text")
            if isinstance(text, str) and text.strip():
                parts.append(text)
                continue
            text_data = chunk.get("text")
            if isinstance(text_data, dict):
                content = text_data.get("content")
                if isinstance(content, str) and content.strip():
                    parts.append(content)
        return "".join(parts).strip()
    if prop_type == "formula":
        formula = prop.get("formula")
        if isinstance(formula, dict):
            for key in ("string", "number", "boolean"):
                value = formula.get(key)
                if value in (None, ""):
                    continue
                if isinstance(value, bool):
                    return "true" if value else "false"
                return str(value).strip()
        return ""
    if prop_type in {"select", "status"}:
        selected = prop.get(prop_type)
        if isinstance(selected, dict):
            name = selected.get("name")
            if isinstance(name, str):
                return name.strip()
        return ""
    if prop_type == "checkbox":
        checkbox = prop.get("checkbox")
        if isinstance(checkbox, bool):
            return "true" if checkbox else "false"
        if checkbox is not None:
            return str(checkbox).strip()
        return ""
    if prop_type == "number":
        number = prop.get("number")
        if number is None:
            return ""
        return str(number).strip()
    if prop_type == "multi_select":
        multi = prop.get("multi_select")
        if isinstance(multi, list):
            names = [
                str(item.get("name", "")).strip()
                for item in multi
                if isinstance(item, dict) and str(item.get("name", "")).strip()
            ]
            return ", ".join(names)
        return ""
    plain_text = prop.get("plain_text")
    if isinstance(plain_text, str):
        return plain_text.strip()
    return ""


def _split_lines(value: str) -> List[str]:
    if not value:
        return []
    cleaned: List[str] = []
    for raw_line in value.replace("\r", "").split("\n"):
        stripped = raw_line.strip()
        if not stripped:
            continue
        stripped = re.sub(r"^[\s\-\u2022•·\*]+", "", stripped).strip()
        if stripped:
            cleaned.append(stripped)
    return cleaned


def _split_tags(value: str) -> List[str]:
    if not value:
        return []
    parts = [part.strip() for part in re.split(r"[,;]", value) if part.strip()]
    return _dedupe_preserve(parts)


def _dedupe_preserve(items: Iterable[str]) -> List[str]:
    seen: Dict[str, None] = {}
    result: List[str] = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen[key] = None
        result.append(item)
    return result


def _ensure_unique_slugs(items: List[SkillOut]) -> List[SkillOut]:
    slug_counts: Dict[str, int] = {}
    result: List[SkillOut] = []
    for skill in items:
        slug = skill.slug
        count = slug_counts.get(slug, 0)
        if count == 0:
            slug_counts[slug] = 1
            result.append(skill)
            continue
        new_index = count + 1
        new_slug = f"{slug}-{new_index}"
        while new_slug in slug_counts:
            new_index += 1
            new_slug = f"{slug}-{new_index}"
        slug_counts[slug] = new_index
        slug_counts[new_slug] = 1
        result.append(skill.model_copy(update={"slug": new_slug, "id": skill.id or new_slug}))
    return result


def _sort_skills(items: List[SkillOut]) -> List[SkillOut]:
    return sorted(
        items,
        key=lambda skill: (
            skill.order is None,
            skill.order if skill.order is not None else 0,
            skill.title.lower(),
        ),
    )


def _slugify(value: str) -> str:
    normalized = _transliterate(value)
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = normalized.strip("-")
    return normalized


def _transliterate(value: str) -> str:
    if not value:
        return ""
    result_chars: List[str] = []
    for char in value:
        lower = char.lower()
        if lower in _CYRILLIC_TRANSLIT:
            translit = _CYRILLIC_TRANSLIT[lower]
            result_chars.append(translit)
        else:
            result_chars.append(char)
    normalized = "".join(result_chars)
    normalized = unicodedata.normalize("NFKD", normalized)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    return normalized


def clear_skills_cache() -> None:
    """Clear cached skills data (intended for tests)."""

    with _cache_lock:
        _skills_cache.clear()



