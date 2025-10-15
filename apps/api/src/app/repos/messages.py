"""Message repository."""
import uuid
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import asyncpg
from app.core.logging import get_logger

logger = get_logger(__name__)


class MessageRepo:
    """Repository for message data."""
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        content_meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add a message to a session."""
        message_id = uuid.uuid4().hex
        content_json = json.dumps({"text": content, "meta": content_meta or {}})
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO messages (id, session_id, role, content_json, ts)
                VALUES ($1, $2, $3, $4, $5)
                """,
                message_id,
                session_id,
                role,
                content_json,
                datetime.now(timezone.utc),
            )
        
        return message_id
    
    async def get_recent_messages(
        self,
        session_id: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Get recent messages for a session."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, role, content_json, ts
                FROM messages
                WHERE session_id = $1
                ORDER BY ts DESC
                LIMIT $2
                """,
                session_id,
                limit,
            )
        
        messages = []
        for row in reversed(rows):  # Reverse to get chronological order
            content_data = json.loads(row["content_json"])
            messages.append({
                "id": row["id"],
                "role": row["role"],
                "content": content_data.get("text", ""),
                "meta": content_data.get("meta", {}),
                "ts": row["ts"],
            })
        
        return messages

