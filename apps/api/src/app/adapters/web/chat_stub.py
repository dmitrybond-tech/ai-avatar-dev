"""Chat stub router - simple rule-based responses without DB."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Literal, Optional
import random

router = APIRouter()

Role = Literal["user", "assistant"]


class HistoryItem(BaseModel):
    role: Role
    text: str


class ChatStubRequest(BaseModel):
    message: str
    history: Optional[List[HistoryItem]] = None


class ChatStubResponse(BaseModel):
    reply: str


GREETINGS = ["hi", "hello", "hey", "привет", "здрав", "yo", "sup", "hola"]
HELP = ["help", "how", "помоги", "как", "что умеешь", "what can you do"]


def rule_based_reply(message: str, history: List[HistoryItem] | None) -> str:
    """Generate a rule-based reply without using any external services."""
    m = message.strip().lower()
    
    if any(g in m for g in GREETINGS):
        return random.choice(
            [
                "Hello! I'm a stub assistant. Ask me something.",
                "Hi there! I can echo and give simple hints.",
                "Привет! Я заглушка-бот — расскажи, что нужно.",
                "Hey! This is a simple demo. How can I help?",
            ]
        )
    
    if any(h in m for h in HELP):
        return (
            "I'm a simple demo assistant. I can greet you and echo your messages. "
            "Try asking a short question — I'll reflect it back with a friendly note."
        )
    
    return f"You said: "{message}". If this were wired to a model, I'd answer helpfully."


@router.post("/api/chat/stub", response_model=ChatStubResponse)
def chat_stub(req: ChatStubRequest) -> ChatStubResponse:
    """Handle chat stub requests with rule-based responses."""
    reply = rule_based_reply(req.message, req.history)
    return ChatStubResponse(reply=reply)

