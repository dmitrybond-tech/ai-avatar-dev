from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


ChatRole = Literal["user", "assistant", "system"]


class ChatMessagePayload(BaseModel):
    role: ChatRole
    content: str = Field(..., min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def _strip_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("content must not be empty")
        return cleaned


class AskRequest(BaseModel):
    messages: List[ChatMessagePayload] = Field(..., min_length=1)
    lang: Literal["en", "ru"] = "ru"
    top_k: int = Field(default=5, ge=1, le=10)
    use_llm: Optional[bool] = True


class AskResponse(BaseModel):
    answer: str
    sources: List[str] = Field(default_factory=list)
    used_llm: bool
    persona: Optional[str] = "dima"


class ExportRequest(BaseModel):
    messages: List[ChatMessagePayload] = Field(default_factory=list)
    title: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


