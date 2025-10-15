"""Chat HTTP router."""
from fastapi import APIRouter, HTTPException, Depends
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import ChatService
from app.repos.sessions import SessionRepo
from app.repos.messages import MessageRepo
from app.db.connection import get_db_pool

router = APIRouter()


def get_chat_service() -> ChatService:
    """Dependency to get chat service."""
    pool = get_db_pool()
    session_repo = SessionRepo(pool)
    message_repo = MessageRepo(pool)
    return ChatService(session_repo, message_repo)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
):
    """Handle non-streaming chat requests."""
    try:
        session_id, answer = await service.chat(
            user_message=request.message,
            session_id=request.session_id,
            persona=request.persona,
        )
        
        return ChatResponse(
            session_id=session_id,
            answer=answer,
            meta={},
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

