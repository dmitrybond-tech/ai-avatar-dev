from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator, Optional

from sqlmodel import Field, Session, SQLModel, create_engine


def _default_timestamp() -> datetime:
    return datetime.now(timezone.utc)


CHAT_DB_URL = os.getenv("CHAT_DB_URL", "sqlite:////app/data/chat.db")
_ECHO = os.getenv("CHAT_DB_ECHO", "").strip().lower() in {"1", "true", "yes", "on"}

_connect_args = {"check_same_thread": False} if CHAT_DB_URL.startswith("sqlite") else {}

engine = create_engine(CHAT_DB_URL, echo=_ECHO, connect_args=_connect_args)


class ChatSession(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    tg_user_id: Optional[int] = Field(default=None, index=True)
    started_at: datetime = Field(default_factory=_default_timestamp, nullable=False)
    exported_at: Optional[datetime] = Field(default=None, nullable=True)
    lang: str = Field(default="ru", nullable=False, max_length=8)


class ChatMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="chatsession.id", nullable=False, index=True)
    role: str = Field(default="user", nullable=False, max_length=16)
    text: str = Field(nullable=False)
    ts: datetime = Field(default_factory=_default_timestamp, nullable=False, index=True)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()

