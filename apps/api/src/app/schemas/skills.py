"""API schemas for Skills endpoints."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

__all__ = ["SkillCard", "SkillDetail"]


class SkillCard(BaseModel):
    """Lightweight skill card representation for list view."""

    slug: str
    title: str
    short: str
    tags: List[str] = Field(default_factory=list)


class SkillDetail(BaseModel):
    """Detailed skill payload for modal view."""

    slug: str
    title: str
    short: str | None = None
    tags: List[str] = Field(default_factory=list)
    bullets: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)

