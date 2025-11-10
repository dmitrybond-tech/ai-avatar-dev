from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Iterable, List, Optional, Sequence

import pandas as pd
from rapidfuzz import fuzz

try:
    from notion_client import Client  # type: ignore
except Exception:  # pragma: no cover - notion client is optional
    Client = None  # type: ignore

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
    lines = []
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


@dataclass(frozen=True)
class SkillRecord:
    key: str
    title_en: str
    title_ru: str
    short_en: str
    short_ru: str
    bullets_en: List[str]
    bullets_ru: List[str]
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

        self._notion_api_key = os.getenv("NOTION_API_KEY") or os.getenv("NOTION_SECRET")
        self._notion_db = os.getenv("NOTION_DB_SKILLS") or os.getenv("NOTION_DB")
        timeout_raw = os.getenv("NOTION_TIMEOUT") or ""
        try:
            self._notion_timeout = float(timeout_raw) if timeout_raw else 10.0
        except ValueError:
            self._notion_timeout = 10.0

        self._csv_path = Path(os.getenv("SKILLS_CSV_PATH") or "/app/data/skills.csv")
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
            "Loaded %s skills (source=%s, notion=%s, csv=%s, mode=%s)",
            len(skills),
            source,
            notion_ok,
            csv_ok,
            self._mode,
        )
        return SkillsSnapshot(skills=skills, source=source, notion=notion_ok, csv_fallback=csv_ok and not notion_ok)

    # Notion helpers -----------------------------------------------------

    def _load_from_notion(self) -> List[SkillRecord]:
        if not self._notion_api_key or not self._notion_db or Client is None:
            return []
        try:
            client = Client(auth=self._notion_api_key, timeout=self._notion_timeout)
        except Exception as exc:  # pragma: no cover - network auth failure
            logger.warning("Failed to init Notion client: %s", exc)
            return []

        try:
            response = client.databases.query(database_id=self._notion_db)  # type: ignore[call-arg]
        except Exception as exc:  # pragma: no cover - network failure
            logger.warning("Notion query failed: %s", exc)
            return []
        results = response.get("results", [])

        records: List[SkillRecord] = []
        for row in results:
            props = row.get("properties", {})
            title_en = _plain_text(props, ["Title EN", "Name", "Title"])
            title_ru = _plain_text(props, ["Title RU", "Title Ru", "Title"])
            short_en = _plain_text(props, ["Short EN", "Summary"])
            short_ru = _plain_text(props, ["Short RU", "Short"])
            slug = _plain_text(props, ["Slug"])
            if not slug:
                slug = _slugify(_clean(title_en or title_ru or ""))
            tags = _multi_select(props, ["Tags", "Tag"])
            bullets_en = _rich_text(props, ["Bullets EN", "Bullets"])
            bullets_ru = _rich_text(props, ["Bullets RU"])
            examples_en = _rich_text(props, ["Examples EN", "Examples"])
            examples_ru = _rich_text(props, ["Examples RU"])

            if not (title_en or title_ru):
                continue

            records.append(
                SkillRecord(
                    key=slug or _slugify(title_en or title_ru),
                    title_en=title_en or title_ru,
                    title_ru=title_ru or title_en,
                    short_en=short_en or short_ru,
                    short_ru=short_ru or short_en,
                    bullets_en=bullets_en or examples_en,
                    bullets_ru=bullets_ru or examples_ru,
                    tags=tags,
                    source="notion",
                )
            )
        return records

    # CSV helpers --------------------------------------------------------

    def _load_from_csv(self) -> List[SkillRecord]:
        if not self._csv_path.exists():
            logger.warning("Skills CSV path %s does not exist", self._csv_path)
            return []
        try:
            df = pd.read_csv(self._csv_path)
        except Exception as exc:  # pragma: no cover - csv failure
            logger.warning("Failed to read CSV %s: %s", self._csv_path, exc)
            return []

        records: List[SkillRecord] = []
        for row in df.to_dict(orient="records"):
            normalized = {str(k).lower(): row[k] for k in row}
            key = _clean(
                normalized.get("key")
                or normalized.get("slug")
                or normalized.get("id")
                or normalized.get("title")
                or normalized.get("titleen")
                or normalized.get("titleru")
            )
            title_en = _clean(normalized.get("titleen") or normalized.get("title") or normalized.get("title_en"))
            title_ru = _clean(normalized.get("titleru") or normalized.get("title_ru") or normalized.get("titlerussian"))
            short_en = _clean(normalized.get("shorten") or normalized.get("short_en") or normalized.get("short"))
            short_ru = _clean(normalized.get("shortru") or normalized.get("short_ru") or normalized.get("shortrussian"))
            bullets_en = _split_lines(
                normalized.get("bulletsen")
                or normalized.get("bullets_en")
                or normalized.get("bullets")
                or normalized.get("examplesen")
            )
            bullets_ru = _split_lines(
                normalized.get("bulletsru")
                or normalized.get("bullets_ru")
                or normalized.get("examplesru")
                or normalized.get("examples_ru")
            )
            tags = _split_tags(
                normalized.get("tags")
                or normalized.get("tagsen")
                or normalized.get("tags_ru")
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
                    tags=tags,
                    source="csv",
                )
            )
        return records

    # Ranking ------------------------------------------------------------

    def relevant_skills(self, query: str, top_k: int) -> List[SkillRecord]:
        snapshot = self.snapshot()
        if not snapshot.skills:
            return []
        cleaned_query = _clean(query).lower()
        if not cleaned_query:
            return snapshot.skills[:top_k]

        scored = []
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
                ]
            ).lower()
            score = fuzz.token_set_ratio(cleaned_query, corpus)
            if score > 0:
                scored.append((score, skill))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [skill for _, skill in scored[:top_k]]


def _slugify(text: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in text)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "skill"


def _plain_text(props: dict, keys: Sequence[str]) -> str:
    for key in keys:
        candidate = props.get(key)
        if not candidate:
            continue
        typ = candidate.get("type")
        if typ == "title":
            items = candidate.get("title", [])
            texts = [item.get("plain_text", "") for item in items if item]
            joined = "".join(texts).strip()
            if joined:
                return joined
        if typ == "rich_text":
            items = candidate.get("rich_text", [])
            texts = [item.get("plain_text", "") for item in items if item]
            joined = "".join(texts).strip()
            if joined:
                return joined
        if typ == "formula":
            string_val = candidate.get("formula", {}).get("string")
            if string_val:
                return str(string_val).strip()
    return ""


def _multi_select(props: dict, keys: Sequence[str]) -> List[str]:
    for key in keys:
        candidate = props.get(key)
        if not candidate:
            continue
        if candidate.get("type") == "multi_select":
            return [item.get("name", "").strip() for item in candidate.get("multi_select", []) if item.get("name")]
    return []


def _rich_text(props: dict, keys: Sequence[str]) -> List[str]:
    lines: List[str] = []
    for key in keys:
        candidate = props.get(key)
        if not candidate:
            continue
        array = candidate.get(candidate.get("type", ""), [])
        for block in array or []:
            text = block.get("plain_text") or block.get("text", {}).get("content")
            if not text:
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

