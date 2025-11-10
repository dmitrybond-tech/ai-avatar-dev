from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _system_prompt(lang: str, skills_snip: str) -> str:
    skills_section = ""
    if skills_snip.strip():
        if lang == "ru":
            skills_section = f"\n\nКонтекст навыков Димы:\n{skills_snip.strip()}"
        else:
            skills_section = f"\n\nDima's skills context:\n{skills_snip.strip()}"

    if lang == "en":
        return (
            "You are Dima's assistant. You always refer to Dima in the third person. "
            "Respond in English unless the user explicitly requests Russian. "
            "Stay concise, helpful, and grounded in verified information. "
            "If something is unclear, admit it honestly."
            f"{skills_section}"
        )
    return (
        "Ты — ассистент Димы. Всегда говори о Диме в третьем лице. "
        "Отвечай на русском языке, если пользователь не попросил иначе. "
        "Будь дружелюбной, но деловой, опирайся на факты и честно говори, если нет данных."
        f"{skills_section}"
    )


def llm_reply(lang: str, user_text: str, skills_snip: str) -> Optional[str]:
    provider = (os.getenv("LLM_PROVIDER") or "openai").strip().lower()
    model = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()
    temperature = _float_env("LLM_TEMPERATURE", 0.2)
    max_tokens = _int_env("LLM_MAX_TOKENS", 600)

    messages = [
        {"role": "system", "content": _system_prompt(lang, skills_snip)},
        {"role": "user", "content": user_text},
    ]

    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("Groq provider selected but GROQ_API_KEY is missing")
            return None
        try:
            from groq import Groq  # type: ignore import-not-found
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to import groq client: %s", exc)
            return None
        client = Groq(api_key=api_key)
        try:
            completion = client.chat.completions.create(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=messages,
            )
        except Exception as exc:  # pragma: no cover - external API
            logger.warning("Groq completion failed: %s", exc)
            return None
        choice = completion.choices[0].message.content if completion.choices else None
        return choice.strip() if isinstance(choice, str) and choice.strip() else None

    if provider != "openai":
        logger.warning("Unsupported LLM provider: %s", provider)
        return None

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OpenAI provider selected but OPENAI_API_KEY is missing")
        return None

    try:
        from openai import OpenAI  # type: ignore import-not-found
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to import openai client: %s", exc)
        return None

    client = OpenAI(api_key=api_key)
    try:
        completion = client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=messages,
        )
    except Exception as exc:  # pragma: no cover - external API
        logger.warning("OpenAI completion failed: %s", exc)
        return None

    choice = completion.choices[0].message.content if completion.choices else None
    return choice.strip() if isinstance(choice, str) and choice.strip() else None

