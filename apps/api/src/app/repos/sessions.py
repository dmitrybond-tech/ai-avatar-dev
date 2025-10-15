"""Session repository."""
import uuid
import json
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import asyncpg
from app.core.logging import get_logger

logger = get_logger(__name__)


class SessionRepo:
    """Repository for session data."""
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    async def create_session(
        self,
        channel: str = "web",
        user_ref: str = "",
        state: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new session."""
        session_id = uuid.uuid4().hex
        state_json = json.dumps(state or {})
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO sessions (id, channel, user_ref, state_json, created_at)
                VALUES ($1, $2, $3, $4, $5)
                """,
                session_id,
                channel,
                user_ref,
                state_json,
                datetime.now(timezone.utc),
            )
        
        logger.info(f"Created session: {session_id}")
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, channel, user_ref, state_json, created_at
                FROM sessions
                WHERE id = $1
                """,
                session_id,
            )
        
        if not row:
            return None
        
        return {
            "id": row["id"],
            "channel": row["channel"],
            "user_ref": row["user_ref"],
            "state": json.loads(row["state_json"]),
            "created_at": row["created_at"],
        }
    
    async def update_session_state(
        self,
        session_id: str,
        state: Dict[str, Any],
    ) -> None:
        """Update session state."""
        state_json = json.dumps(state)
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE sessions
                SET state_json = $1
                WHERE id = $2
                """,
                state_json,
                session_id,
            )

