"""Chat-related schemas."""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Chat request payload."""
    session_id: Optional[str] = None
    message: str = Field(..., min_length=1, max_length=4000)
    persona: Optional[str] = None
    params: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Chat response payload."""
    session_id: str
    answer: str
    meta: Optional[Dict[str, Any]] = None


class TTSRequest(BaseModel):
    """Text-to-speech request."""
    text: str = Field(..., min_length=1, max_length=500)
    voice_preset: Optional[str] = None


class TTSResponse(BaseModel):
    """Text-to-speech response."""
    audio_url: str
    duration_sec: float


class TelegramVerifyRequest(BaseModel):
    """Telegram initData verification request."""
    init_data: str


class TelegramVerifyResponse(BaseModel):
    """Telegram initData verification response."""
    session_token: str
    session_id: str

