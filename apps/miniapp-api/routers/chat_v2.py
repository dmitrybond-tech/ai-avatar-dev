from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status

from ..models.chat import AskRequest, AskResponse, ChatMessage, ExportRequest
from ..services.llm import LLMProvider
from ..services.skills import SkillsRepository, SkillRecord, best_query_from_messages
from ..services.telegram import TelegramExporter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


def get_skills_repo(request: Request) -> SkillsRepository:
    repo = getattr(request.app.state, "skills_repo", None)
    if repo is None:
        raise RuntimeError("skills repository not initialized")
    return repo


def get_llm_provider(request: Request) -> LLMProvider:
    provider = getattr(request.app.state, "llm_provider", None)
    if provider is None:
        raise RuntimeError("llm provider not initialized")
    return provider


def get_telegram_exporter(request: Request) -> TelegramExporter:
    exporter = getattr(request.app.state, "telegram_exporter", None)
    if exporter is None:
        raise RuntimeError("telegram exporter not initialized")
    return exporter


@router.get("/config")
async def get_config(
    skills_repo: SkillsRepository = Depends(get_skills_repo),
    llm_provider: LLMProvider = Depends(get_llm_provider),
    telegram: TelegramExporter = Depends(get_telegram_exporter),
) -> Dict[str, Any]:
    snapshot = skills_repo.snapshot()
    return {
        "persona": llm_provider.persona,
        "llmAvailable": llm_provider.available,
        "notion": snapshot.notion,
        "csvFallback": snapshot.csv_fallback,
        "telegramExport": telegram.available,
        "model": llm_provider.model,
    }


@router.get("/healthz")
async def api_healthz(
    request: Request,
    skills_repo: SkillsRepository = Depends(get_skills_repo),
    llm_provider: LLMProvider = Depends(get_llm_provider),
) -> Dict[str, Any]:
    start = getattr(request.app.state, "start_time", None)
    uptime = time.time() - start if start else 0.0
    snapshot = skills_repo.snapshot()
    return {
        "ok": True,
        "uptime_s": round(uptime, 2),
        "skills_source": snapshot.source or "unknown",
        "llm": "ok" if llm_provider.available else "missing",
    }


@router.post("/client-log", status_code=status.HTTP_202_ACCEPTED)
async def client_log(
    payload: Dict[str, Any] = Body(default_factory=dict),
) -> Dict[str, Any]:
    request_id = f"log-{int(time.time() * 1000)}"
    logger.info("client-log %s %s", request_id, payload)
    return {"ok": True, "request_id": request_id}


@router.post("/ask", response_model=AskResponse)
async def ask(
    body: AskRequest,
    skills_repo: SkillsRepository = Depends(get_skills_repo),
    llm_provider: LLMProvider = Depends(get_llm_provider),
) -> AskResponse:
    user_messages = [message.content for message in body.messages if message.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "missing_user_message"})

    query = best_query_from_messages(user_messages[-3:])
    top_skills: List[SkillRecord] = skills_repo.relevant_skills(query, body.top_k)

    deterministic_answer = build_deterministic_answer(body.lang, top_skills)
    used_llm = False

    if body.use_llm and llm_provider.available and query:
        context_lines = build_context(body.lang, top_skills)
        user_prompt = build_user_prompt(query, user_messages, context_lines)
        system_prompt = build_system_prompt(body.lang)
        llm_answer = await llm_provider.generate(system_prompt, user_prompt)
        if llm_answer:
            deterministic_answer = llm_answer
            used_llm = True

    sources = [skill.key for skill in top_skills] if top_skills else []
    return AskResponse(
        answer=deterministic_answer,
        sources=sources,
        used_llm=used_llm,
        persona=llm_provider.persona,
    )


@router.post("/export/telegram")
async def export_telegram(
    request: Request,
    body: ExportRequest,
    dry_run: bool = Query(default=False, alias="dryRun"),
    exporter: TelegramExporter = Depends(get_telegram_exporter),
) -> Dict[str, Any]:
    if not exporter.available and not dry_run:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"error": "telegram_unavailable"})

    payload_messages = body.messages or []
    meta = body.meta or {}
    meta.update(
        {
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        }
    )
    try:
        result = await exporter.send(
            [ChatMessage(role=msg.role, content=msg.content) for msg in payload_messages],
            meta=meta,
            title=body.title,
            dry_run=dry_run,
        )
    except Exception as exc:
        logger.warning("Telegram export failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail={"error": "telegram_failed"}) from exc
    return result


def build_context(lang: str, skills: List[SkillRecord]) -> str:
    if not skills:
        return ""
    lines: List[str] = []
    for skill in skills:
        lines.append(f"{skill.title(lang)} — {skill.summary(lang)}")
        for bullet in skill.bullets(lang)[:2]:
            lines.append(f"- {bullet}")
    return "\n".join(lines)


def build_user_prompt(query: str, user_messages: List[str], context: str) -> str:
    history = "\n\n".join(f"User said: {message}" for message in user_messages[-3:])
    prompt = f"{history}\n\nLast question:\n{query}"
    if context:
        prompt += f"\n\nRelevant skills:\n{context}"
    return prompt


def build_system_prompt(lang: str) -> str:
    base = (
        "Answer as Dima's assistant. Prefer concrete capabilities from the provided skills. "
        "If something is outside the skills, say how Dima can still help."
    )
    if lang == "ru":
        return base + " Отвечай на русском языке и будь лаконичным."
    return base + " Answer in English and keep it concise."


def build_deterministic_answer(lang: str, skills: List[SkillRecord]) -> str:
    if not skills:
        return (
            "Я пока ищу нужную информацию, но могу рассказать об опыте Димы и подобрать релевантные навыки."
            if lang == "ru"
            else "I’ll clarify Dima’s current focus and find the most relevant skills that might help."
        )

    if lang == "ru":
        header = "Вот чем Дима может помочь:"
        bullets = [f"• {skill.title('ru')}: {skill.summary('ru')}" for skill in skills[:3]]
        extra = skills[0].bullets("ru") if skills else []
        for line in extra:
            if len(bullets) >= 4:
                break
            bullets.append(f"• {line}")
        while len(bullets) < 2:
            bullets.append("• Подберёт подход и поможет связаться с нужными экспертами.")
        closing = "Если задача отличается, Дима предложит подход или познакомит с нужными людьми."
        return "\n".join([header, *bullets[:4], closing])

    header = "Here is how Dima can help:"
    bullets = [f"- {skill.title('en')}: {skill.summary('en')}" for skill in skills[:3]]
    extra = skills[0].bullets("en") if skills else []
    for line in extra:
        if len(bullets) >= 4:
            break
        bullets.append(f"- {line}")
    while len(bullets) < 2:
        bullets.append("- He can outline next steps and connect you with the right specialists.")
    closing = "If your request is a bit different, Dima can still suggest a path or connect you with the right person."
    return "\n".join([header, *bullets[:4], closing])

