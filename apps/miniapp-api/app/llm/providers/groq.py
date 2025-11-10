from __future__ import annotations

import os
from typing import Any, Dict, Tuple

import httpx

DEFAULT_BASE_URL = "https://api.groq.com/openai"


class GroqConfigError(RuntimeError):
    """Raised when Groq configuration is incomplete."""


async def generate_groq(draft: str, system: str, temperature: float = 0.2) -> Tuple[str, Dict[str, Any]]:
    """
    Call Groq's OpenAI-compatible chat completion endpoint.

    Args:
        draft: User payload (includes question/context/draft answer).
        system: System prompt guiding the assistant.
        temperature: Sampling temperature.

    Returns:
        A tuple of (reply_text, usage_dict).
    """

    api_key = (os.getenv("GROQ_API_KEY") or "").strip()
    if not api_key:
        raise GroqConfigError("GROQ_API_KEY is not set")

    base_url = (os.getenv("GROQ_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    model = (os.getenv("LLM_MODEL") or os.getenv("SMART_CHAT_LLM_MODEL") or "").strip()
    if not model:
        raise GroqConfigError("LLM_MODEL is not set for Groq provider")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    org_id = (os.getenv("GROQ_ORG_ID") or "").strip()
    if org_id:
        headers["X-Organization"] = org_id

    payload = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": draft},
        ],
    }

    async with httpx.AsyncClient(base_url=base_url, timeout=20.0) as client:
        response = await client.post("/chat/completions", json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    try:
        message = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError("Groq response is missing completion text") from None

    usage = data.get("usage") or {}
    reply = message.strip()
    if not reply:
        raise RuntimeError("Groq returned an empty completion")

    return reply, usage


