"""Chat WebSocket router."""
import json
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.services.chat import ChatService
from app.repos.sessions import SessionRepo
from app.repos.messages import MessageRepo
from app.db.connection import get_db_pool
from app.core.logging import get_logger
from app.core.security import verify_session_token

router = APIRouter()
logger = get_logger(__name__)


@router.websocket("/chat/stream")
async def chat_stream(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """WebSocket endpoint for streaming chat."""
    await websocket.accept()
    
    # Extract session_id from token if provided
    session_id = None
    if token:
        payload = verify_session_token(token)
        if payload:
            session_id = payload.get("session_id")
    
    # Send connected message
    await websocket.send_json({
        "type": "connected",
        "session_id": session_id,
    })
    
    # Initialize services
    pool = get_db_pool()
    session_repo = SessionRepo(pool)
    message_repo = MessageRepo(pool)
    service = ChatService(session_repo, message_repo)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                if message.get("type") == "user_message":
                    text = message.get("text", "")
                    if not text:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Empty message",
                        })
                        continue
                    
                    # Override session_id if provided in message
                    msg_session_id = message.get("session_id") or session_id
                    persona = message.get("persona")
                    
                    # Stream response
                    async for sid, delta in service.chat_stream(
                        user_message=text,
                        session_id=msg_session_id,
                        persona=persona,
                    ):
                        session_id = sid
                        await websocket.send_json({
                            "type": "partial",
                            "delta": delta,
                        })
                    
                    # Send final message
                    await websocket.send_json({
                        "type": "final",
                        "text": "",  # Full text already streamed
                        "session_id": session_id,
                    })
                
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                })
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                })
    
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")

