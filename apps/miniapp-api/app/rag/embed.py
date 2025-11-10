from __future__ import annotations

import os
import threading
from typing import Iterable

import numpy as np
from sentence_transformers import SentenceTransformer

_EMBED_MODEL_LOCK = threading.Lock()
_EMBEDDER: SentenceTransformer | None = None


def get_model_name() -> str:
    return os.getenv("EMB_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")


def get_embedder() -> SentenceTransformer:
    global _EMBEDDER
    if _EMBEDDER is None:
        with _EMBED_MODEL_LOCK:
            if _EMBEDDER is None:
                model_name = get_model_name()
                _EMBEDDER = SentenceTransformer(model_name, device="cpu")
    return _EMBEDDER


def embed_texts(texts: Iterable[str]) -> np.ndarray:
    embedder = get_embedder()
    vectors = embedder.encode(
        list(texts),
        convert_to_numpy=True,
        normalize_embeddings=False,
        show_progress_bar=False,
    )
    if vectors.dtype != np.float32:
        vectors = vectors.astype("float32")
    return vectors


