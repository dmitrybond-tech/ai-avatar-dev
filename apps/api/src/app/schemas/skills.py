"""Pydantic schemas for Skills API."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class SkillOut(BaseModel):
    """Skill projection for list/detail responses."""

    id: str
    slug: str
    name: str
    short: str
    long: str
    tags: List[str] = Field(default_factory=list)
    category: Optional[str] = None
    icon: Optional[str] = None
    order: Optional[int] = None



