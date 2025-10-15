"""Chat service with streaming support."""
import asyncio
from typing import AsyncGenerator, List, Optional
from app.core.logging import get_logger
from app.repos.sessions import SessionRepo
from app.repos.messages import MessageRepo

logger = get_logger(__name__)


class LLMProvider:
    """Base LLM provider interface."""
    
    async def stream_chat(
        self,
        messages: List[dict],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion."""
        raise NotImplementedError


class StubLLMProvider(LLMProvider):
    """Stub LLM provider for testing (echo with transform)."""
    
    async def stream_chat(
        self,
        messages: List[dict],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Echo last user message with slight transform and delay."""
        if not messages:
            yield "Hello! How can I help you?"
            return
        
        last_message = messages[-1].get("content", "")
        response = f"Echo: {last_message[:100]}"
        
        # Simulate streaming with word-by-word output
        words = response.split()
        for word in words:
            await asyncio.sleep(0.05)  # 50ms delay per word
            yield word + " "


class ChatService:
    """Chat orchestration service."""
    
    def __init__(
        self,
        session_repo: SessionRepo,
        message_repo: MessageRepo,
        llm_provider: Optional[LLMProvider] = None,
    ):
        self.session_repo = session_repo
        self.message_repo = message_repo
        self.llm_provider = llm_provider or StubLLMProvider()
    
    async def chat_stream(
        self,
        user_message: str,
        session_id: Optional[str] = None,
        channel: str = "web",
        user_ref: str = "",
        persona: Optional[str] = None,
    ) -> AsyncGenerator[tuple[str, str], None]:
        """
        Stream chat response.
        
        Yields: (session_id, delta) tuples.
        """
        # Get or create session
        if not session_id:
            session_id = await self.session_repo.create_session(
                channel=channel,
                user_ref=user_ref,
            )
        
        # Store user message
        await self.message_repo.add_message(
            session_id=session_id,
            role="user",
            content=user_message,
        )
        
        # Retrieve recent messages for context (last 5)
        history = await self.message_repo.get_recent_messages(session_id, limit=5)
        
        # Build messages for LLM
        messages = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in history
        ]
        messages.append({"role": "user", "content": user_message})
        
        # Stream response
        full_response = ""
        async for delta in self.llm_provider.stream_chat(messages, persona=persona):
            full_response += delta
            yield (session_id, delta)
        
        # Store assistant message
        await self.message_repo.add_message(
            session_id=session_id,
            role="assistant",
            content=full_response.strip(),
        )
    
    async def chat(
        self,
        user_message: str,
        session_id: Optional[str] = None,
        channel: str = "web",
        user_ref: str = "",
        persona: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        Non-streaming chat.
        
        Returns: (session_id, full_response)
        """
        full_response = ""
        async for sid, delta in self.chat_stream(
            user_message=user_message,
            session_id=session_id,
            channel=channel,
            user_ref=user_ref,
            persona=persona,
        ):
            session_id = sid
            full_response += delta
        
        return session_id, full_response.strip()

