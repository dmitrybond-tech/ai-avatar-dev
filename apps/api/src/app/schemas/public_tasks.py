"""Pydantic schemas for public tasks API."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class PublicTaskOut(BaseModel):
    """Output model for public task listing."""
    id: str
    title: str
    status: str
    progress_pct: int = Field(..., ge=0, le=100)
    review_at: Optional[str] = None
    last_updated: str
    tags: List[str] = Field(default_factory=list)
    url: str


class PublicTaskCreate(BaseModel):
    """Model for creating a task."""
    title: str = Field(..., min_length=1, max_length=200)
    status: Optional[str] = None
    scope: Optional[int] = Field(None, ge=0)
    done: Optional[int] = Field(None, ge=0)
    review_at: Optional[datetime] = None
    tags: Optional[List[str]] = Field(None, max_length=10)
    source: Optional[str] = Field("MiniApp", max_length=20)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid_statuses = {"Backlog", "In Progress", "Review", "Blocked", "Done"}
            if v not in valid_statuses:
                raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid_sources = {"MiniApp", "Bot", "Manual"}
            if v not in valid_sources:
                raise ValueError(f"Source must be one of: {', '.join(valid_sources)}")
        return v


class PublicTaskUpdate(BaseModel):
    """Update model for partial task updates."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    status: Optional[str] = None
    scope: Optional[int] = Field(None, ge=0)
    done: Optional[int] = Field(None, ge=0)
    review_at: Optional[datetime] = None
    tags: Optional[List[str]] = Field(None, max_length=10)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid_statuses = {"Backlog", "In Progress", "Review", "Blocked", "Done"}
            if v not in valid_statuses:
                raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v


class CommentRequest(BaseModel):
    """Request model for adding a comment."""
    text: str = Field(..., min_length=1, max_length=1000)

