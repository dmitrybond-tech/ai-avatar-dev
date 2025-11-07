"""Skills data provider with Notion primary source and CSV fallback."""
from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Literal, Optional, Sequence, Tuple

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


@dataclass(slots=True)
class _FetchMeta:
    source: str = "unknown"
    fallback: bool = False
    count: int = 0


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


_TITLE_PRIMARY: Dict[Lang, Tuple[str, ...]] = {
    "en": ("Title EN", "Title (EN)", "EN Title"),
    "ru": ("Title RU", "Title (RU)", "RU Title"),
}
_SHORT_PRIMARY: Dict[Lang, Tuple[str, ...]] = {
    "en": ("Short EN", "Short (EN)", "EN Short"),
    "ru": ("Short RU", "Short (RU)", "RU Short"),
}
_BULLETS_PRIMARY: Dict[Lang, Tuple[str, ...]] = {
    "en": ("Bullets EN", "Bullets (EN)", "EN Bullets"),
    "ru": ("Bullets RU", "Bullets (RU)", "RU Bullets"),
}
_EXAMPLES_PRIMARY: Dict[Lang, Tuple[str, ...]] = {
    "en": ("Examples EN", "Examples (EN)", "EN Examples"),
    "ru": ("Examples RU", "Examples (RU)", "RU Examples"),
}

_TITLE_SHARED = ("Title", "Name", "Название")
_SHORT_SHARED = ("Short", "Summary", "Описание")
_BULLETS_SHARED = ("Bullets", "Details", "Описание")
_EXAMPLES_SHARED = ("Examples", "Use Cases", "Примеры")

_TAGS_CANDIDATES = (
    "Tags",
    "Tag",
    "Skill Tags",
    "Tags EN",
    "Tags RU",
)
_ORDER_CANDIDATES = ("Order", "Sort", "Position")
_SLUG_CANDIDATES = ("Slug", "slug", "URL", "Link")

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
    source_mode = _resolve_source_mode()

    if source_mode is SkillsSourceMode.CSV:
        skills = _load_from_csv(normalized_lang)
        _store_fetch_meta("csv", False, len(skills))
        return skills

    if source_mode is SkillsSourceMode.NOTION:
        try:
            skills = _load_from_notion(normalized_lang)
            _store_fetch_meta("notion", False, len(skills))
            return skills
        except SkillsSourceError as exc:  # pragma: no cover - configuration/network
            _store_fetch_meta("notion", False, 0)
            raise SkillsUnavailableError(str(exc)) from exc

    # auto mode
    try:
        skills = _load_from_notion(normalized_lang)
        _store_fetch_meta("notion", False, len(skills))
        return skills
    except SkillsSourceError as exc:
        logger.warning(
            "skills_source=fallback_csv reason=%s file=%s",
            exc,
            _resolve_csv_path(),
        )
        skills = _load_from_csv(normalized_lang)
        _store_fetch_meta("csv", True, len(skills))
        return skills


def _store_fetch_meta(source: str, fallback: bool, count: int) -> None:
    global _last_fetch_meta
    _last_fetch_meta = _FetchMeta(source=source, fallback=fallback, count=count)


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
    else:
        candidate = base_api_dir / "data" / "skills.csv"
    if not candidate.is_absolute():
        candidate = (base_api_dir / candidate).resolve()
    return candidate


def _load_from_csv(lang: Lang) -> List[SkillOut]:
    path = _resolve_csv_path()
    if not path.exists():
        raise SkillsUnavailableError(f"CSV file not found: {path}")

    items: List[SkillOut] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        for index, row in enumerate(rows, start=1):
            title_key = f"Title {'EN' if lang == 'en' else 'RU'}"
            short_key = f"Short {'EN' if lang == 'en' else 'RU'}"
            bullets_key = f"Bullets {'EN' if lang == 'en' else 'RU'}"
            examples_key = f"Examples {'EN' if lang == 'en' else 'RU'}"

            title = (row.get(title_key) or row.get("Title") or "").strip()
            if not title:
                logger.warning(
                    "skills_source=csv row=%d missing_title keys=[%s]",
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
                    index += 1
                    if isinstance(page, dict):
                        skill = _notion_page_to_skill(page, lang, index)
                        if skill is not None:
                            items.append(skill)

            if not response.get("has_more"):
                break
            next_cursor = response.get("next_cursor")
            if isinstance(next_cursor, str) and next_cursor:
                start_cursor = next_cursor
            else:
                break

        unique = _ensure_unique_slugs(items)
        return _sort_skills(unique)
    except APIResponseError as exc:  # pragma: no cover - network path
        logger.error(
            "skills_source=notion error=%s message=%s request_id=%s",
            exc.code,
            exc.message,
            getattr(exc, "request_id", ""),
        )
        raise SkillsUnavailableError(f"Notion API error: {exc.message}") from exc
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("skills_source=notion error=%s", exc, exc_info=True)
        raise SkillsUnavailableError("Failed to fetch skills from Notion") from exc


def _notion_page_to_skill(page: Dict[str, object], lang: Lang, index: int) -> Optional[SkillOut]:
    props = page.get("properties")
    if not isinstance(props, dict):
        return None

    page_id = str(page.get("id") or "")
    logs: List[Tuple[str, Sequence[str], Optional[str]]] = []

    other_lang: Lang = "ru" if lang == "en" else "en"

    title_candidates = list(_TITLE_PRIMARY.get(lang, ()))
    fallback_title = list(_TITLE_SHARED) + list(_TITLE_PRIMARY.get(other_lang, ()))
    title, title_used = _pick_text(props, title_candidates, fallback_title, logs, field="title")
    if not title:
        logger.warning("skills_source=notion page_id=%s missing_title", page_id)
        return None

    slug = _extract_slug(props, title)

    short_candidates = list(_SHORT_PRIMARY.get(lang, ()))
    fallback_short = list(_SHORT_SHARED) + list(_SHORT_PRIMARY.get(other_lang, ()))
    short, short_used = _pick_text(props, short_candidates, fallback_short, logs, field="short", optional=True)
    if not short:
        short = title

    bullets_candidates = list(_BULLETS_PRIMARY.get(lang, ()))
    fallback_bullets = list(_BULLETS_SHARED) + list(_BULLETS_PRIMARY.get(other_lang, ()))
    bullets_text, bullets_used = _pick_text(props, bullets_candidates, fallback_bullets, logs, field="bullets", optional=True)
    bullets = _split_lines(bullets_text)

    examples_candidates = list(_EXAMPLES_PRIMARY.get(lang, ()))
    fallback_examples = list(_EXAMPLES_SHARED) + list(_EXAMPLES_PRIMARY.get(other_lang, ()))
    examples_text, examples_used = _pick_text(props, examples_candidates, fallback_examples, logs, field="examples", optional=True)
    examples = _split_lines(examples_text)

    tags = _extract_tags(props)
    order = _extract_order(props)

    for field_name, primary, used in logs:
        if not primary:
            continue
        expected = primary[0] if isinstance(primary, Sequence) and primary else ""
        if used is None:
            logger.warning(
                "skills_source=notion slug=%s page_id=%s field=%s missing_property=%s",
                slug,
                page_id,
                field_name,
                expected,
            )
        elif used not in primary:
            logger.warning(
                "skills_source=notion slug=%s page_id=%s field=%s missing_property=%s fallback_property=%s",
                slug,
                page_id,
                field_name,
                expected,
                used,
            )

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


def _pick_text(
    props: Dict[str, Dict[str, object]],
    primary: Sequence[str],
    fallback: Sequence[str],
    logs: List[Tuple[str, Sequence[str], Optional[str]]],
    *,
    field: str,
    optional: bool = False,
) -> Tuple[str, Optional[str]]:
    for name in primary:
        value = _rich_text(props.get(name))
        if value:
            return value, name

    for name in fallback:
        value = _rich_text(props.get(name))
        if value:
            logs.append((field, primary, name))
            return value, name

    if not optional:
        logs.append((field, primary, None))
    return "", None


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
    if prop_type not in {"rich_text", "title"}:
        return ""
    chunks = prop.get(prop_type)
    if not isinstance(chunks, list):
        return ""
    parts: List[str] = []
    for chunk in chunks:
        if isinstance(chunk, dict):
            text = chunk.get("plain_text")
            if isinstance(text, str):
                parts.append(text)
    return "".join(parts).strip()


def _split_lines(value: str) -> List[str]:
    if not value:
        return []
    return [line.strip() for line in value.replace("\r", "").split("\n") if line.strip()]


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



