"""Telegram service for sending briefs."""
import os
import html
import httpx
from app.core.logging import get_logger

logger = get_logger(__name__)


async def send_brief(
    admin_chat_id: int,
    bot_token: str,
    path_to_file: str,
    caption: str,
) -> bool:
    """
    Send a brief file to Telegram admin.
    
    Args:
        admin_chat_id: Telegram chat ID of the admin
        bot_token: Telegram bot token
        path_to_file: Path to the file to send
        caption: Caption text (HTML formatted)
    
    Returns:
        True if sent successfully, False otherwise
    """
    if not admin_chat_id or not bot_token:
        logger.warning("Telegram not configured: missing admin_chat_id or bot_token")
        return False
    
    if not os.path.exists(path_to_file):
        logger.error(f"File not found: {path_to_file}")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            with open(path_to_file, "rb") as fh:
                file_name = os.path.basename(path_to_file)
                data = {
                    "chat_id": admin_chat_id,
                    "caption": caption,
                    "parse_mode": "HTML",
                }
                files = {
                    "document": (file_name, fh, "application/octet-stream")
                }
                response = await client.post(url, data=data, files=files)
                
                if response.status_code < 400:
                    logger.info(f"Brief sent to Telegram successfully: {file_name}")
                    return True
                else:
                    logger.warning(
                        f"Telegram send failed: status={response.status_code}, "
                        f"response={response.text[:200]}"
                    )
                    return False
    except Exception as e:
        logger.error(f"Failed to send brief to Telegram: {e}", exc_info=True)
        return False


def build_caption(
    request_id: str,
    locale: str,
    name: str,
    company: str,
    phone: str,
    email: str,
    message: str | None = None,
) -> str:
    """
    Build HTML-formatted caption for Telegram message.
    
    Args:
        request_id: Request ID
        locale: Locale code
        name: Name
        company: Company name
        phone: Phone number
        email: Email address
        message: Optional message/comment
    
    Returns:
        HTML-formatted caption string
    """
    parts = [
        f"<b>New Brief</b> ({locale.upper()})",
        f"<b>Request ID:</b> {html.escape(request_id)}",
        f"<b>Name:</b> {html.escape(name)}",
        f"<b>Company:</b> {html.escape(company)}",
        f"<b>Phone:</b> {html.escape(phone)}",
        f"<b>Email:</b> {html.escape(email)}",
    ]
    
    if message and message.strip():
        parts.append(f"<b>Comment:</b> {html.escape(message.strip())}")
    
    return "\n".join(parts)

