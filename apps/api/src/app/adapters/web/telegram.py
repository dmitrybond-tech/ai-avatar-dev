"""Telegram verification router."""
from fastapi import APIRouter, HTTPException
from app.schemas.chat import TelegramVerifyRequest, TelegramVerifyResponse
from app.core.security import verify_telegram_init_data, create_session_token
from app.repos.sessions import SessionRepo
from app.db.connection import get_db_pool
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/tg/verify", response_model=TelegramVerifyResponse)
async def verify_telegram(request: TelegramVerifyRequest):
    """Verify Telegram WebApp initData and create session."""
    # Verify HMAC
    parsed_data = verify_telegram_init_data(request.init_data)
    if not parsed_data:
        raise HTTPException(status_code=401, detail="Invalid Telegram data")
    
    # Extract user info
    # Telegram sends user data as JSON string in the 'user' field
    import json as json_lib
    user_data_str = parsed_data.get("user", "{}")
    try:
        user_data = json_lib.loads(user_data_str)
        user_id = user_data.get("id", "")
    except (json_lib.JSONDecodeError, AttributeError):
        user_id = ""
    
    user_ref = f"tg_{user_id}" if user_id else "tg_unknown"
    
    # Create session
    pool = get_db_pool()
    session_repo = SessionRepo(pool)
    session_id = await session_repo.create_session(
        channel="telegram",
        user_ref=user_ref,
    )
    
    # Generate session token
    session_token = create_session_token(session_id, user_ref)
    
    logger.info(f"Telegram user verified: {user_ref}, session: {session_id}")
    
    return TelegramVerifyResponse(
        session_token=session_token,
        session_id=session_id,
    )

