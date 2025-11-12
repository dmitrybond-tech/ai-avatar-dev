"""FatContext builder: combines chat history + skills for Grok."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from .chat_store import get_chat_store
from .skills import SkillsRepository, best_query_from_messages

logger = logging.getLogger(__name__)

# Default limits
DEFAULT_FAT_MSG_LIMIT = 30
DEFAULT_FAT_BYTES_LIMIT = 24576  # 24KB
DEFAULT_FAT_SKILL_TOPK = 5


def build_fat_context(
    session_id: str,
    q: str,
    lang: str,
    selected_skills: Optional[List[str]] = None,
    skills_repo: Optional[SkillsRepository] = None,
) -> Dict[str, Any]:
    """
    Build FatContext from chat history + relevant skills.
    
    Args:
        session_id: Chat session ID
        q: User question
        lang: Language (ru|en)
        selected_skills: Optional list of skill slugs to include
        skills_repo: Optional skills repository (uses global if None)
    
    Returns:
        Dict with keys: dialog_recent, skills_excerpt, session_meta
    """
    # Get limits from env
    msg_limit = int(os.getenv("FAT_MSG_LIMIT", DEFAULT_FAT_MSG_LIMIT))
    bytes_limit = int(os.getenv("FAT_BYTES_LIMIT", DEFAULT_FAT_BYTES_LIMIT))
    skill_topk = int(os.getenv("FAT_SKILL_TOPK", DEFAULT_FAT_SKILL_TOPK))
    
    # Normalize lang
    if lang not in {"ru", "en"}:
        lang = "en"
    
    # Load recent messages
    chat_store = get_chat_store()
    events = chat_store.read_tail(session_id, limit=msg_limit)
    
    # Extract dialog (role/content only, compact)
    dialog_recent: List[Dict[str, str]] = []
    total_bytes = 0
    
    # Process events in reverse (newest first) but keep last turns
    # Keep all messages that mention skills, plus last N turns
    skill_mentions: List[Dict[str, str]] = []
    last_turns: List[Dict[str, str]] = []
    
    # Track last few turns
    turn_buffer: List[Dict[str, str]] = []
    for event in reversed(events):
        role = event.get("role", "")
        content = event.get("content", "")
        if not content or role not in {"user", "assistant", "grok"}:
            continue
        
        msg = {"role": role, "content": content}
        msg_bytes = len(content.encode("utf-8"))
        
        # Check if message mentions any skills (simple keyword check)
        content_lower = content.lower()
        if any(keyword in content_lower for keyword in ["skill", "competence", "capability", "ability", "навык", "компетенция"]):
            skill_mentions.append(msg)
        
        turn_buffer.insert(0, msg)
        if len(turn_buffer) > 6:  # Keep last 3 turns (6 messages)
            turn_buffer.pop()
    
    # Combine: skill mentions + last turns (dedupe)
    seen = set()
    for msg in skill_mentions + turn_buffer:
        key = (msg["role"], msg["content"][:50])  # Simple dedupe key
        if key not in seen:
            seen.add(key)
            dialog_recent.append(msg)
            total_bytes += len(msg["content"].encode("utf-8"))
            if total_bytes >= bytes_limit:
                break
    
    # Reverse to chronological order
    dialog_recent.reverse()
    
    # Truncate if still too large
    while total_bytes > bytes_limit and len(dialog_recent) > 1:
        removed = dialog_recent.pop(0)
        total_bytes -= len(removed["content"].encode("utf-8"))
    
    # Select relevant skills
    if skills_repo is None:
        # Create new repository if not provided
        skills_repo = SkillsRepository()
    
    snapshot = skills_repo.snapshot()
    selected_skill_records: List[Any] = []
    
    if selected_skills:
        # Use provided skills
        for slug in selected_skills:
            skill = next((s for s in snapshot.skills if s.key == slug), None)
            if skill:
                selected_skill_records.append(skill)
    
    if not selected_skill_records:
        # Build query from q + recent messages
        query_texts = [q]
        for msg in dialog_recent[-3:]:  # Last 3 messages
            query_texts.append(msg.get("content", ""))
        
        query = best_query_from_messages(query_texts)
        if not query:
            query = q
        
        # Search for relevant skills
        selected_skill_records = skills_repo.relevant_skills(query, top_k=skill_topk)
    
    # Build skills excerpt
    skills_excerpt: List[Dict[str, Any]] = []
    for skill in selected_skill_records[:skill_topk]:
        skill_info: Dict[str, Any] = {
            "slug": skill.key,
            "title": skill.title(lang),
            "short": skill.summary(lang),
        }
        bullets = skill.bullets(lang)
        if bullets:
            skill_info["bullets"] = bullets[:3]  # Limit bullets
        examples = skill.examples(lang)
        if examples:
            skill_info["examples"] = examples[:2]  # Limit examples
        if skill.tags:
            skill_info["tags"] = skill.tags
        skills_excerpt.append(skill_info)
    
    # Build session meta
    session_meta: Dict[str, Any] = {
        "session_id": session_id,
        "lang": lang,
        "message_count": len(events),
        "dialog_turns": len(dialog_recent),
        "skills_count": len(skills_excerpt),
    }
    
    return {
        "dialog_recent": dialog_recent,
        "skills_excerpt": skills_excerpt,
        "session_meta": session_meta,
    }


def format_fat_context_for_grok(context: Dict[str, Any]) -> str:
    """
    Format FatContext dict into a string prompt for Grok.
    
    Args:
        context: Output from build_fat_context
    
    Returns:
        Formatted string prompt
    """
    dialog_recent = context.get("dialog_recent", [])
    skills_excerpt = context.get("skills_excerpt", [])
    session_meta = context.get("session_meta", {})
    
    parts: List[str] = []
    
    # Add dialog context
    if dialog_recent:
        parts.append("Recent conversation:")
        for msg in dialog_recent:
            role = msg.get("role", "")
            content = msg.get("content", "")
            parts.append(f"{role}: {content}")
        parts.append("")
    
    # Add skills context
    if skills_excerpt:
        parts.append("Relevant skills and capabilities:")
        for skill in skills_excerpt:
            skill_parts = [f"Skill: {skill.get('title', '')}"]
            if skill.get("short"):
                skill_parts.append(f"Summary: {skill.get('short')}")
            if skill.get("tags"):
                skill_parts.append(f"Tags: {', '.join(skill.get('tags', []))}")
            if skill.get("bullets"):
                bullets_text = "; ".join(skill.get("bullets", [])[:3])
                skill_parts.append(f"Capabilities: {bullets_text}")
            if skill.get("examples"):
                examples_text = "; ".join(skill.get("examples", [])[:2])
                skill_parts.append(f"Examples: {examples_text}")
            parts.append("\n".join(skill_parts))
        parts.append("")
    
    return "\n".join(parts)

