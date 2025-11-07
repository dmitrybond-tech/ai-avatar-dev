"""Router exports for the miniapp API."""

from __future__ import annotations

from . import briefs  # re-export for backwards compatibility
from . import public_tasks  # re-export for backwards compatibility
from .skills import router as skills

__all__ = ["skills", "briefs", "public_tasks"]


