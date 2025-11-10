from __future__ import annotations

import logging
import os
from typing import List, Optional

try:
    from openai import AsyncOpenAI  # type: ignore
except Exception:  # pragma: no cover - optional dependency guard
    AsyncOpenAI = None  # type: ignore

logger = logging.getLogger(__name__)


class LLMProvider:
    def __init__(self) -> None:
        self._api_key = os.getenv("OPENAI_API_KEY") or os.getenv("SMART_CHAT_OPENAI_KEY")
        self._model = os.getenv("LLM_MODEL") or os.getenv("SMART_CHAT_LLM_MODEL") or "gpt-4o-mini"
        self._client: Optional[AsyncOpenAI] = None
        if self._api_key and AsyncOpenAI is not None:
            try:
                self._client = AsyncOpenAI(api_key=self._api_key)
            except Exception as exc:  # pragma: no cover - runtime guard
                logger.warning("Failed to initialize OpenAI client: %s", exc)
                self._client = None
        self._persona = os.getenv("CHAT_PERSONA") or "dima"

    @property
    def persona(self) -> str:
        return self._persona

    @property
    def model(self) -> Optional[str]:
        return self._model if self.available else None

    @property
    def available(self) -> bool:
        return self._client is not None

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> Optional[str]:
        if not self._client:
            return None
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as exc:  # pragma: no cover - SDK/network failure
            logger.warning("LLM completion failed: %s", exc)
            return None
        try:
            message = response.choices[0].message.content  # type: ignore[attr-defined]
        except (AttributeError, IndexError, KeyError, TypeError):
            return None
        if isinstance(message, str):
            cleaned = message.strip()
            return cleaned or None
        if isinstance(message, list):
            joined = " ".join(part.get("text", "") for part in message if isinstance(part, dict))
            return joined.strip() or None
        return None

