"""Security utilities."""
import hashlib
import hmac
import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from urllib.parse import parse_qsl
from app.core.settings import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def verify_telegram_init_data(init_data: str) -> Optional[Dict[str, str]]:
    """
    Verify Telegram WebApp initData HMAC.
    
    Returns parsed data dict if valid, None otherwise.
    """
    try:
        # Parse init data
        parsed = dict(parse_qsl(init_data))
        received_hash = parsed.pop("hash", None)
        
        if not received_hash:
            logger.warning("No hash in initData")
            return None
        
        # Check auth_date (must be within 5 minutes)
        auth_date = parsed.get("auth_date")
        if not auth_date:
            logger.warning("No auth_date in initData")
            return None
        
        auth_timestamp = int(auth_date)
        now_timestamp = int(datetime.now(timezone.utc).timestamp())
        
        if abs(now_timestamp - auth_timestamp) > 300:  # 5 minutes
            logger.warning("initData too old or from future")
            return None
        
        # Build data check string
        data_check_items = [f"{k}={v}" for k, v in sorted(parsed.items())]
        data_check_string = "\n".join(data_check_items)
        
        # Compute secret key: HMAC-SHA256(BOT_TOKEN, "WebAppData")
        secret_key = hmac.new(
            b"WebAppData",
            settings.telegram_bot_token.encode(),
            hashlib.sha256
        ).digest()
        
        # Compute expected hash
        expected_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(expected_hash, received_hash):
            logger.warning("HMAC verification failed")
            return None
        
        return parsed
    
    except Exception as e:
        logger.error(f"Failed to verify Telegram initData: {e}")
        return None


def create_session_token(session_id: str, user_ref: str = "") -> str:
    """Create a JWT session token."""
    payload = {
        "session_id": session_id,
        "user_ref": user_ref,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=settings.jwt_ttl_seconds),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def verify_session_token(token: str) -> Optional[Dict]:
    """Verify and decode a JWT session token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None

