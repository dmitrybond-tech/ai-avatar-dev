from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import faiss  # type: ignore
import numpy as np

from . import loader
from .embed import embed_texts, get_model_name


@dataclass(frozen=True)
class SearchHit:
    record: loader.SkillRecord
    score: float


@dataclass
class IndexBundle:
    index: faiss.Index
    records: List[loader.SkillRecord]
    model: str
    vector_dim: int
    source_mtime: float


_INDEX_CACHE: Optional[IndexBundle] = None
_INDEX_LOCK = threading.Lock()


def _resolve_cache_paths() -> tuple[Path, Path]:
    csv_path = loader.resolve_csv_path()
    base_dir = csv_path.parent
    index_path = Path(os.getenv("SKILLS_FAISS_PATH", str(base_dir / "skills.faiss"))).expanduser()
    meta_path = Path(os.getenv("SKILLS_EMBED_META_PATH", str(base_dir / "skills.embeddings.json"))).expanduser()
    index_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    return index_path, meta_path


def get_index_bundle() -> IndexBundle:
    global _INDEX_CACHE
    if _INDEX_CACHE is not None:
        return _INDEX_CACHE

    with _INDEX_LOCK:
        if _INDEX_CACHE is None:
            _INDEX_CACHE = _load_or_build()
    return _INDEX_CACHE


def _load_or_build() -> IndexBundle:
    index_path, meta_path = _resolve_cache_paths()
    model_name = get_model_name()
    csv_path = loader.resolve_csv_path()
    try:
        source_mtime = csv_path.stat().st_mtime
    except FileNotFoundError as exc:  # pragma: no cover - runtime guard
        raise FileNotFoundError(f"Skills CSV not found at {csv_path}") from exc

    if index_path.exists() and meta_path.exists():
        bundle = _try_load_cached(index_path, meta_path)
        if bundle and bundle.model == model_name and abs(bundle.source_mtime - source_mtime) < 1e-6:
            return bundle

    return _build_index(index_path, meta_path, source_mtime, model_name)


def _try_load_cached(index_path: Path, meta_path: Path) -> Optional[IndexBundle]:
    try:
        with meta_path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception:
        return None

    try:
        index = faiss.read_index(str(index_path))
    except Exception:
        return None

    try:
        records = [
            loader.SkillRecord(
                id=item["id"],
                lang=item["lang"],
                title=item["title"],
                short=item.get("short"),
                tags=list(item.get("tags", [])),
                bullets=list(item.get("bullets", [])),
                examples=list(item.get("examples", [])),
                slug=item.get("slug", ""),
            )
            for item in payload["records"]
        ]
        source_mtime = float(payload["source_mtime"])
        model = str(payload["model"])
        vector_dim = int(payload["vector_dim"])
    except Exception:
        return None

    if index.ntotal != len(records) or index.d != vector_dim:
        return None

    return IndexBundle(
        index=index,
        records=records,
        model=model,
        vector_dim=vector_dim,
        source_mtime=source_mtime,
    )


def _build_index(index_path: Path, meta_path: Path, source_mtime: float, model_name: str) -> IndexBundle:
    records = loader.load_skills()
    if not records:
        raise RuntimeError("No skills records are available to build FAISS index")

    corpus_texts = [_record_to_text(record) for record in records]
    embeddings = embed_texts(corpus_texts)
    if embeddings.ndim != 2:
        raise RuntimeError("Embeddings must be a 2D array")

    embeddings = np.ascontiguousarray(embeddings, dtype="float32")
    faiss.normalize_L2(embeddings)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    faiss.write_index(index, str(index_path))

    meta_payload = {
        "model": model_name,
        "source_mtime": source_mtime,
        "vector_dim": dim,
        "records": [
            {
                "id": record.id,
                "lang": record.lang,
                "title": record.title,
                "short": record.short,
                "tags": record.tags,
                "bullets": record.bullets,
                "examples": record.examples,
                "slug": record.slug,
            }
            for record in records
        ],
    }

    with meta_path.open("w", encoding="utf-8") as fh:
        json.dump(meta_payload, fh, ensure_ascii=False, indent=2)

    return IndexBundle(
        index=index,
        records=records,
        model=model_name,
        vector_dim=dim,
        source_mtime=source_mtime,
    )


def search(embedding: np.ndarray, top_k: int, preferred_lang: Optional[str] = None) -> List[SearchHit]:
    if top_k <= 0:
        return []

    bundle = get_index_bundle()
    if bundle.index.ntotal == 0:
        return []
    query = np.asarray(embedding, dtype="float32").reshape(1, -1)
    faiss.normalize_L2(query)

    search_k = min(max(top_k * 3, top_k, 1), bundle.index.ntotal)
    distances, indices = bundle.index.search(query, search_k)
    raw_hits: List[SearchHit] = []
    for score, idx in zip(distances[0], indices[0]):
        if idx < 0 or idx >= len(bundle.records):
            continue
        record = bundle.records[idx]
        raw_hits.append(SearchHit(record=record, score=float(score)))

    if not preferred_lang:
        return raw_hits[:top_k]

    same_lang = [hit for hit in raw_hits if hit.record.lang == preferred_lang]
    if len(same_lang) >= top_k:
        return same_lang[:top_k]

    fallback = [hit for hit in raw_hits if hit.record.lang != preferred_lang]
    return (same_lang + fallback)[:top_k]


def _record_to_text(record: loader.SkillRecord) -> str:
    parts = [record.title]
    if record.short:
        parts.append(record.short)
    if record.bullets:
        parts.append(" ".join(record.bullets))
    if record.examples:
        parts.append(" ".join(record.examples))
    if record.tags:
        parts.append(" ".join(record.tags))
    return " ".join(parts)


