from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

ChatRole = Literal["user", "assistant", "system"]


class ChatMessage(BaseModel):
    role: ChatRole
    content: str = Field(..., min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("content must not be empty")
        return cleaned


class AskRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., min_length=1)
    lang: Literal["en", "ru"] = "ru"
    top_k: int = Field(default=5, ge=1, le=10)
    use_llm: Optional[bool] = True


class AskResponse(BaseModel):
    answer: str
    sources: List[str] = Field(default_factory=list)
    used_llm: bool
    persona: Optional[str] = "dima"


class ExportRequest(BaseModel):
    conv_id: Optional[str] = None
    lang: Optional[Literal["en", "ru"]] = None
    messages: List[ChatMessage] = Field(default_factory=list)
    items: Optional[List[ChatMessage]] = Field(default=None)
    title: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

