from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd
from rapidfuzz import fuzz

try:
    from notion_client import Client  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Client = None  # type: ignore

from apps.miniapp_api.core import env as env_utils


logger = logging.getLogger(__name__)


def _clean(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _split_lines(value: object) -> List[str]:
    text = _clean(value)
    if not text:
        return []
    normalized = text.replace(";", "\n")
    lines: List[str] = []
    for raw in normalized.splitlines():
        cleaned = raw.strip(" •-\t")
        if cleaned:
            lines.append(cleaned)
    return lines


def _split_tags(value: object) -> List[str]:
    text = _clean(value)
    if not text:
        return []
    tokens = [token.strip() for token in text.replace(";", ",").split(",")]
    return [token for token in tokens if token]


def _normalize_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


@dataclass(frozen=True)
class SkillRecord:
    key: str
    title_en: str
    title_ru: str
    short_en: str
    short_ru: str
    bullets_en: List[str]
    bullets_ru: List[str]
    examples_en: List[str]
    examples_ru: List[str]
    tags: List[str]
    source: str

    def title(self, lang: str) -> str:
        if lang.startswith("ru"):
            return self.title_ru or self.title_en or self.key
        return self.title_en or self.title_ru or self.key

    def summary(self, lang: str) -> str:
        if lang.startswith("ru"):
            return self.short_ru or self.short_en
        return self.short_en or self.short_ru

    def bullets(self, lang: str) -> List[str]:
        if lang.startswith("ru"):
            return self.bullets_ru or self.bullets_en
        return self.bullets_en or self.bullets_ru

    def examples(self, lang: str) -> List[str]:
        if lang.startswith("ru"):
            return self.examples_ru or self.examples_en
        return self.examples_en or self.examples_ru


@dataclass
class SkillsSnapshot:
    skills: List[SkillRecord]
    source: str
    notion: bool
    csv_fallback: bool


class SkillsRepository:
    def __init__(self) -> None:
        self._lock = Lock()
        self._snapshot: Optional[SkillsSnapshot] = None

        self._notion_api_key = env_utils.notion_token()
        self._notion_db = env_utils.skills_db()
        self._notion_timeout = float(env_utils.notion_timeout())

        default_csv = Path(__file__).resolve().parent.parent / "data" / "skills.csv"
        configured_csv = (os.getenv("SKILLS_CSV_PATH") or str(default_csv)).strip()
        self._csv_path = Path(configured_csv)
        self._mode = (os.getenv("SKILLS_SOURCE") or "auto").strip().lower()

    def refresh(self) -> SkillsSnapshot:
        with self._lock:
            self._snapshot = self._load_snapshot()
            return self._snapshot

    def snapshot(self) -> SkillsSnapshot:
        with self._lock:
            if self._snapshot is None:
                self._snapshot = self._load_snapshot()
            return self._snapshot

    def relevant_skills(self, query: str, top_k: int) -> List[SkillRecord]:
        snapshot = self.snapshot()
        if not snapshot.skills:
            return []
        cleaned_query = _clean(query).lower()
        if not cleaned_query:
            return snapshot.skills[:top_k]

        scored: List[Tuple[int, SkillRecord]] = []
        for skill in snapshot.skills:
            corpus = " ".join(
                [
                    skill.title_en,
                    skill.title_ru,
                    skill.short_en,
                    skill.short_ru,
                    " ".join(skill.tags),
                    " ".join(skill.bullets_en[:3]),
                    " ".join(skill.bullets_ru[:3]),
                    " ".join(skill.examples_en[:2]),
                    " ".join(skill.examples_ru[:2]),
                ]
            ).lower()
            score = fuzz.token_set_ratio(cleaned_query, corpus)
            if score > 0:
                scored.append((score, skill))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [skill for _, skill in scored[:top_k]]

    # Internal helpers -------------------------------------------------

    def _load_snapshot(self) -> SkillsSnapshot:
        notion_skills: List[SkillRecord] = []
        csv_skills: List[SkillRecord] = []
        source = "unknown"
        notion_ok = False
        csv_ok = False

        if self._mode in {"auto", "notion"}:
            notion_skills = self._load_from_notion()
            if notion_skills:
                notion_ok = True
                source = "notion"

        if (self._mode in {"auto", "csv"} and not notion_skills) or self._mode == "csv":
            csv_skills = self._load_from_csv()
            if csv_skills:
                csv_ok = True
                if not notion_skills:
                    source = "csv"

        skills = notion_skills or csv_skills
        logger.info(
            "skills_loaded count=%s source=%s notion=%s csv=%s mode=%s",
            len(skills),
            source,
            notion_ok,
            csv_ok,
            self._mode,
        )
        return SkillsSnapshot(skills=skills, source=source, notion=notion_ok, csv_fallback=csv_ok and not notion_ok)

    def _load_from_notion(self) -> List[SkillRecord]:
        if not self._notion_api_key or not self._notion_db or Client is None:
            return []
        try:
            client = Client(auth=self._notion_api_key, timeout=self._notion_timeout)
        except Exception as exc:  # pragma: no cover - client init failure
            logger.warning("notion_init_failed error=%s", exc)
            return []
        try:
            response = client.databases.query(database_id=self._notion_db)  # type: ignore[call-arg]
        except Exception as exc:  # pragma: no cover - network failure
            logger.warning("notion_query_failed error=%s", exc)
            return []
        results = response.get("results", [])
        records: List[SkillRecord] = []
        for row in results:
            record = self._map_notion_record(row)
            if record:
                records.append(record)
        return records

    def _map_notion_record(self, row: Dict[str, object]) -> Optional[SkillRecord]:
        props = row.get("properties", {}) if isinstance(row, dict) else {}
        props = props if isinstance(props, dict) else {}
        title_en = _plain_text(props, ["Title EN", "Name", "Title"])
        title_ru = _plain_text(props, ["Title RU", "Title Ru", "Title"])
        if not (title_en or title_ru):
            return None
        short_en = _plain_text(props, ["Short EN", "Summary"])
        short_ru = _plain_text(props, ["Short RU", "Short"])
        slug = _plain_text(props, ["Slug", "Key", "ID"])
        key = _slugify(slug or title_en or title_ru or "")
        bullets_en = _rich_list(props, ["Bullets EN", "Bullets"])
        bullets_ru = _rich_list(props, ["Bullets RU"])
        examples_en = _rich_list(props, ["Examples EN", "Examples"])
        examples_ru = _rich_list(props, ["Examples RU"])
        tags = _multi_select(props, ["Tags", "Tag"])
        return SkillRecord(
            key=key,
            title_en=title_en or title_ru,
            title_ru=title_ru or title_en,
            short_en=short_en or short_ru,
            short_ru=short_ru or short_en,
            bullets_en=bullets_en or examples_en,
            bullets_ru=bullets_ru or examples_ru,
            examples_en=examples_en or bullets_en,
            examples_ru=examples_ru or bullets_ru,
            tags=tags,
            source="notion",
        )

    def _load_from_csv(self) -> List[SkillRecord]:
        if not self._csv_path.exists():
            logger.warning("skills_csv_missing path=%s", self._csv_path)
            return []
        try:
            df = pd.read_csv(self._csv_path)
        except Exception as exc:  # pragma: no cover - csv failure
            logger.warning("skills_csv_read_failed path=%s error=%s", self._csv_path, exc)
            return []
        records: List[SkillRecord] = []
        for row in df.to_dict(orient="records"):
            normalized = {_normalize_key(str(k)): row[k] for k in row}
            key = _clean(
                normalized.get("key")
                or normalized.get("slug")
                or normalized.get("id")
                or normalized.get("title")
                or normalized.get("titleen")
                or normalized.get("titleru")
            )
            title_en = _clean(
                normalized.get("titleen")
                or normalized.get("title")
                or normalized.get("nameen")
                or normalized.get("name")
            )
            title_ru = _clean(
                normalized.get("titleru")
                or normalized.get("titlerussian")
                or normalized.get("nameru")
            )
            short_en = _clean(
                normalized.get("shorten")
                or normalized.get("short")
                or normalized.get("summaryen")
            )
            short_ru = _clean(
                normalized.get("shortru")
                or normalized.get("shortrussian")
                or normalized.get("summaryru")
            )
            bullets_en = _split_lines(
                normalized.get("bulletsen")
                or normalized.get("bullets")
                or normalized.get("examplesen")
            )
            bullets_ru = _split_lines(
                normalized.get("bulletsru")
                or normalized.get("examplesru")
            )
            examples_en = _split_lines(
                normalized.get("examplesen")
                or normalized.get("caseen")
                or normalized.get("casesen")
            )
            examples_ru = _split_lines(
                normalized.get("examplesru")
                or normalized.get("caseru")
                or normalized.get("casesru")
            )
            tags = _split_tags(
                normalized.get("tags")
                or normalized.get("tagsen")
                or normalized.get("tagsru")
            )
            if not key:
                key = _slugify(title_en or title_ru or "skill")
            if not (title_en or title_ru):
                continue
            records.append(
                SkillRecord(
                    key=key,
                    title_en=title_en or title_ru,
                    title_ru=title_ru or title_en,
                    short_en=short_en or short_ru,
                    short_ru=short_ru or short_en,
                    bullets_en=bullets_en,
                    bullets_ru=bullets_ru,
                    examples_en=examples_en or bullets_en,
                    examples_ru=examples_ru or bullets_ru,
                    tags=tags,
                    source="csv",
                )
            )
        return records


def _slugify(text: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in text)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "skill"


def _plain_text(props: Dict[str, object], keys: Sequence[str]) -> str:
    for key in keys:
        candidate = props.get(key)
        if not isinstance(candidate, dict):
            continue
        typ = candidate.get("type")
        if typ == "title":
            items = candidate.get("title", [])
            texts = [item.get("plain_text", "") for item in items if isinstance(item, dict)]
            joined = "".join(texts).strip()
            if joined:
                return joined
        if typ == "rich_text":
            items = candidate.get("rich_text", [])
            texts = [item.get("plain_text", "") for item in items if isinstance(item, dict)]
            joined = "".join(texts).strip()
            if joined:
                return joined
        if typ == "formula":
            formula = candidate.get("formula", {})
            if isinstance(formula, dict):
                for attr in ("string", "number"):
                    value = formula.get(attr)
                    if value not in (None, ""):
                        return str(value).strip()
        plain = candidate.get("plain_text")
        if isinstance(plain, str) and plain.strip():
            return plain.strip()
    return ""


def _multi_select(props: Dict[str, object], keys: Sequence[str]) -> List[str]:
    for key in keys:
        candidate = props.get(key)
        if not isinstance(candidate, dict):
            continue
        if candidate.get("type") == "multi_select":
            return [
                item.get("name", "").strip()
                for item in candidate.get("multi_select", [])
                if isinstance(item, dict) and item.get("name")
            ]
    return []


def _rich_list(props: Dict[str, object], keys: Sequence[str]) -> List[str]:
    lines: List[str] = []
    for key in keys:
        candidate = props.get(key)
        if not isinstance(candidate, dict):
            continue
        array = candidate.get(candidate.get("type", ""), [])
        for block in array or []:
            if not isinstance(block, dict):
                continue
            text = block.get("plain_text") or block.get("text", {}).get("content")
            if not isinstance(text, str):
                continue
            for line in text.splitlines():
                cleaned = line.strip(" •-\t")
                if cleaned:
                    lines.append(cleaned)
    return lines


def best_query_from_messages(messages: Iterable[str]) -> str:
    texts = [text.strip() for text in messages if text and text.strip()]
    if not texts:
        return ""
    if len(texts) == 1:
        return texts[0]
    return " ".join(texts[-3:])


