from __future__ import annotations

from typing import List, Sequence, Tuple

from .index_faiss import SearchHit

Lang = str


def build_extractive_answer(query: str, hits: Sequence[SearchHit], lang: Lang) -> Tuple[str, List[dict]]:
    if not hits:
        if lang == "en":
            reply = (
                "I don't have a ready-made skill card for that yet. "
                "Share a bit more context and I'll connect it with what I can do."
            )
        else:
            reply = (
                "Пока нет точного навыка под ваш запрос. "
                "Расскажите детали, и я сопоставлю это с тем, что умею."
            )
        return reply, []

    titles = [hit.record.title for hit in hits[:3]]
    if lang == "en":
        intro = "I can help with " + ", ".join(titles) + "."
        example_label = "For example"
    else:
        intro = "Могу помочь с " + ", ".join(titles) + "."
        example_label = "Например"

    examples = _collect_examples(hits, limit=3)
    if examples:
        reply = intro + f" {example_label}: " + "; ".join(examples) + "."
    else:
        reply = intro

    sources = []
    for hit in hits[:3]:
        score = float(hit.score)
        score = max(0.0, min(1.0, score))
        sources.append(
            {
                "id": hit.record.id,
                "title": hit.record.title,
                "score": round(score, 4),
            }
        )

    return reply, sources


def _collect_examples(hits: Sequence[SearchHit], limit: int) -> List[str]:
    collected: List[str] = []
    for hit in hits:
        for example in hit.record.examples:
            example_clean = example.strip()
            if not example_clean:
                continue
            collected.append(example_clean)
            if len(collected) >= limit:
                return collected
    # If we did not reach the limit, fall back to bullets for variety
    for hit in hits:
        for bullet in hit.record.bullets:
            bullet_clean = bullet.strip()
            if not bullet_clean:
                continue
            collected.append(bullet_clean)
            if len(collected) >= limit:
                return collected
    return collected


