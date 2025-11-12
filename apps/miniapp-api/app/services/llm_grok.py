"""xAI Grok LLM provider integration."""
from __future__ import annotations

import logging
import os
from typing import List, Optional

try:
    from xai_sdk import Client  # type: ignore
except ImportError:
    Client = None  # type: ignore

logger = logging.getLogger(__name__)

# Default system prompt template
DEFAULT_SYSTEM_PROMPT = (
    "You are Dima's capability assistant. "
    "Answer strictly based on the provided skills context; "
    "if information is missing, say what's known and avoid hallucinations. "
    "Be concise and helpful."
)


class GrokClient:
    """xAI Grok client wrapper."""

    def __init__(self) -> None:
        self._api_key = os.getenv("XAI_API_KEY")
        self._model = os.getenv("GROK_MODEL", "grok-4")
        self._base_url = os.getenv("GROK_BASE_URL", "https://api.x.ai")
        self._max_tokens = int(os.getenv("GROK_MAX_TOKENS", "512"))
        self._temperature = float(os.getenv("GROK_TEMPERATURE", "0.3"))
        self._timeout = 30.0  # 30 seconds timeout
        self._client: Optional[Client] = None

        if not self._api_key:
            logger.warning("XAI_API_KEY not set; Grok client will be unavailable")
        elif Client is None:
            logger.warning("xai-sdk not installed; Grok client will be unavailable")
        else:
            try:
                # Initialize xAI SDK client
                self._client = Client(api_key=self._api_key)
                logger.info("Grok client initialized (model=%s, base_url=%s)", self._model, self._base_url)
            except Exception as exc:
                logger.error("Failed to initialize Grok client: %s", exc, exc_info=True)
                self._client = None

    @property
    def available(self) -> bool:
        """Check if Grok client is available."""
        return self._client is not None and self._api_key is not None

    def ask_grok(self, system_prompt: str, messages: List[dict]) -> Optional[str]:
        """
        Ask Grok a question with system prompt and messages.

        Args:
            system_prompt: System prompt string
            messages: List of message dicts with 'role' and 'content' keys

        Returns:
            Response text or None on error
        """
        if not self.available:
            logger.warning("Grok client not available")
            return None

        try:
            # Build messages list with system prompt
            chat_messages: List[dict] = []
            if system_prompt:
                chat_messages.append({"role": "system", "content": system_prompt})
            chat_messages.extend(messages)

            # Call xAI SDK - try both possible API patterns
            try:
                # Try chat.completions.create pattern (OpenAI-compatible)
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=chat_messages,
                    max_tokens=self._max_tokens,
                    temperature=self._temperature,
                )
            except AttributeError:
                # Fallback to chat.create pattern
                response = self._client.chat.create(
                    model=self._model,
                    messages=chat_messages,
                    max_tokens=self._max_tokens,
                    temperature=self._temperature,
                )

            # Extract response text
            if hasattr(response, "choices") and response.choices:
                message = response.choices[0].message
                if hasattr(message, "content"):
                    content = message.content
                else:
                    content = getattr(message, "text", None) or str(message)
                
                if isinstance(content, str):
                    return content.strip()
                elif isinstance(content, list):
                    # Handle list of content parts
                    parts = [str(p.get("text", "")) if isinstance(p, dict) else str(p) for p in content]
                    return " ".join(parts).strip()

            logger.warning("Unexpected response format from Grok")
            return None

        except Exception as exc:
            logger.error("Grok API call failed: %s", exc, exc_info=True)
            return None

    def ask_with_context(
        self,
        user_question: str,
        skills_context: str,
        system_prompt: Optional[str] = None,
    ) -> Optional[str]:
        """
        Ask Grok with skills context.

        Args:
            user_question: User's question
            skills_context: Formatted skills context string
            system_prompt: Optional custom system prompt

        Returns:
            Response text or None on error
        """
        prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

        # Build context message
        context_message = f"Skills context:\n{skills_context}\n\nUser question: {user_question}"

        messages = [{"role": "user", "content": context_message}]

        return self.ask_grok(prompt, messages)


# Global singleton instance
_grok_client: Optional[GrokClient] = None


def get_grok_client() -> GrokClient:
    """Get or create the global Grok client instance."""
    global _grok_client
    if _grok_client is None:
        _grok_client = GrokClient()
    return _grok_client


def ask_grok(system_prompt: str, messages: List[dict]) -> Optional[str]:
    """Convenience function to ask Grok."""
    return get_grok_client().ask_grok(system_prompt, messages)

