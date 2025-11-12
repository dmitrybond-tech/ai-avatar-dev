"""Chat storage service using JSONL files."""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)

# Default values
DEFAULT_CHAT_DIR = "/app/data/chats"
DEFAULT_ROTATE_MAX_LINES = 1000
DEFAULT_REDACT_EXPORT = True

# Redaction patterns (basic)
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
CARD_PATTERN = re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b')
TOKEN_PATTERN = re.compile(r'\b(bearer|token|api[_-]?key)[\s:=]+[\w-]{20,}\b', re.IGNORECASE)


def _redact_text(text: str, enabled: bool = True) -> str:
    """Basic redaction of sensitive patterns."""
    if not enabled:
        return text
    result = text
    result = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", result)
    result = CARD_PATTERN.sub("[CARD_REDACTED]", result)
    result = TOKEN_PATTERN.sub("[TOKEN_REDACTED]", result)
    return result


class ChatStore:
    """File-based chat storage using JSONL format."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._chat_dir = Path(os.getenv("CHAT_DIR", DEFAULT_CHAT_DIR))
        self._rotate_max_lines = int(os.getenv("FAT_ROTATE_MAX_LINES", DEFAULT_ROTATE_MAX_LINES))
        self._redact_export = os.getenv("REDACT_EXPORT", str(DEFAULT_REDACT_EXPORT)).strip().lower() in {"1", "true", "yes"}
        
        # Ensure directory exists
        self._chat_dir.mkdir(parents=True, exist_ok=True)
        logger.info("ChatStore initialized: dir=%s, rotate_max_lines=%d, redact=%s", 
                   self._chat_dir, self._rotate_max_lines, self._redact_export)

    def _get_session_file(self, session_id: str, create_new: bool = False) -> Path:
        """Get the current file path for a session. If create_new, generate new filename."""
        today = datetime.now(timezone.utc).strftime("%y%m%d")
        if create_new:
            # Generate new file with timestamp
            timestamp = datetime.now(timezone.utc).strftime("%H%M%S")
            return self._chat_dir / f"session-{session_id}-{today}-{timestamp}.jsonl"
        # Find the most recent file for this session
        pattern = f"session-{session_id}-*.jsonl"
        matches = sorted(self._chat_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
        if matches:
            return matches[0]
        # Default filename if no existing file
        return self._chat_dir / f"session-{session_id}-{today}.jsonl"

    def _should_rotate(self, file_path: Path) -> bool:
        """Check if file should be rotated based on line count."""
        if not file_path.exists():
            return False
        try:
            with file_path.open("r", encoding="utf-8") as f:
                line_count = sum(1 for _ in f)
            return line_count >= self._rotate_max_lines
        except Exception as exc:
            logger.warning("Failed to check rotation for %s: %s", file_path, exc)
            return False

    def append_event(
        self,
        session_id: Optional[str],
        role: str,
        content: str,
        lang: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> tuple[str, str]:
        """
        Append an event to the chat store.
        
        Returns:
            (session_id, timestamp_iso)
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Validate role
        allowed_roles = {"user", "assistant", "system", "bot", "grok"}
        if role not in allowed_roles:
            role = "user"
        
        # Normalize lang
        if lang not in {"ru", "en"}:
            lang = "en"
        
        # Build event
        event: Dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "role": role,
            "content": content,
            "lang": lang,
            "meta": meta or {},
        }
        
        with self._lock:
            file_path = self._get_session_file(session_id, create_new=False)
            
            # Check if rotation needed
            if self._should_rotate(file_path):
                file_path = self._get_session_file(session_id, create_new=True)
            
            # Append JSONL line
            try:
                with file_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(event, ensure_ascii=False) + "\n")
            except Exception as exc:
                logger.error("Failed to append event to %s: %s", file_path, exc)
                raise
        
        return session_id, event["ts"]

    def read_tail(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Read last N messages from session files."""
        if limit <= 0:
            return []
        
        # Find all files for this session, sorted by modification time (newest first)
        pattern = f"session-{session_id}-*.jsonl"
        files = sorted(self._chat_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
        
        if not files:
            return []
        
        events: List[Dict[str, Any]] = []
        
        # Read from newest files first until we have enough
        for file_path in files:
            if len(events) >= limit:
                break
            try:
                with file_path.open("r", encoding="utf-8") as f:
                    lines = f.readlines()
                    # Process lines in reverse (newest last)
                    for line in reversed(lines):
                        if len(events) >= limit:
                            break
                        try:
                            event = json.loads(line.strip())
                            if event.get("session_id") == session_id:
                                events.insert(0, event)  # Insert at beginning to maintain order
                        except json.JSONDecodeError:
                            continue
            except Exception as exc:
                logger.warning("Failed to read %s: %s", file_path, exc)
                continue
        
        return events[-limit:] if len(events) > limit else events

    def stream_jsonl(self, session_id: str, redact: Optional[bool] = None) -> Iterator[str]:
        """Stream all events for a session as JSONL lines."""
        pattern = f"session-{session_id}-*.jsonl"
        files = sorted(self._chat_dir.glob(pattern), key=lambda p: p.stat().st_mtime)
        
        redact_enabled = self._redact_export if redact is None else redact
        
        for file_path in files:
            try:
                with file_path.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            event = json.loads(line)
                            if event.get("session_id") == session_id:
                                if redact_enabled:
                                    event["content"] = _redact_text(event.get("content", ""), enabled=True)
                                yield json.dumps(event, ensure_ascii=False) + "\n"
                        except json.JSONDecodeError:
                            continue
            except Exception as exc:
                logger.warning("Failed to stream from %s: %s", file_path, exc)
                continue

    def export_csv(self, session_id: str, redact: Optional[bool] = None) -> Iterator[str]:
        """Export events as CSV lines."""
        redact_enabled = self._redact_export if redact is None else redact
        
        # CSV header
        yield "ts,role,content,lang,used_skills,provider,model,channel,session_id\n"
        
        pattern = f"session-{session_id}-*.jsonl"
        files = sorted(self._chat_dir.glob(pattern), key=lambda p: p.stat().st_mtime)
        
        for file_path in files:
            try:
                with file_path.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            event = json.loads(line)
                            if event.get("session_id") != session_id:
                                continue
                            
                            meta = event.get("meta", {})
                            used_skills = meta.get("used_skills", [])
                            llm_info = meta.get("llm", {})
                            provider = llm_info.get("provider", "")
                            model = llm_info.get("model", "")
                            channel = meta.get("channel", "")
                            
                            content = event.get("content", "")
                            if redact_enabled:
                                content = _redact_text(content, enabled=True)
                            
                            # CSV escaping
                            def csv_escape(s: str) -> str:
                                s = str(s).replace('"', '""')
                                if "," in s or "\n" in s or '"' in s:
                                    return f'"{s}"'
                                return s
                            
                            row = [
                                event.get("ts", ""),
                                event.get("role", ""),
                                csv_escape(content),
                                event.get("lang", ""),
                                csv_escape(",".join(used_skills) if isinstance(used_skills, list) else ""),
                                provider,
                                model,
                                channel,
                                session_id,
                            ]
                            yield ",".join(row) + "\n"
                        except json.JSONDecodeError:
                            continue
            except Exception as exc:
                logger.warning("Failed to export CSV from %s: %s", file_path, exc)
                continue

    def export_txt(self, session_id: str, redact: Optional[bool] = None) -> Iterator[str]:
        """Export events as plain text transcript."""
        redact_enabled = self._redact_export if redact is None else redact
        
        pattern = f"session-{session_id}-*.jsonl"
        files = sorted(self._chat_dir.glob(pattern), key=lambda p: p.stat().st_mtime)
        
        for file_path in files:
            try:
                with file_path.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            event = json.loads(line)
                            if event.get("session_id") != session_id:
                                continue
                            
                            ts = event.get("ts", "")
                            role = event.get("role", "")
                            content = event.get("content", "")
                            
                            if redact_enabled:
                                content = _redact_text(content, enabled=True)
                            
                            # Format: "2025-11-12T08:41:00Z user: Hello"
                            yield f"{ts} {role}: {content}\n"
                        except json.JSONDecodeError:
                            continue
            except Exception as exc:
                logger.warning("Failed to export TXT from %s: %s", file_path, exc)
                continue


# Global singleton
_chat_store: Optional[ChatStore] = None


def get_chat_store() -> ChatStore:
    """Get or create the global chat store instance."""
    global _chat_store
    if _chat_store is None:
        _chat_store = ChatStore()
    return _chat_store

