"""Notion service for creating brief pages."""
import asyncio
from typing import Optional
from notion_client import Client, APIResponseError
from app.core.logging import get_logger

logger = get_logger(__name__)


async def create_brief_page(
    notion_token: str,
    db_id: str,
    data: dict,
) -> Optional[str]:
    """
    Create a brief page in Notion database.
    
    Args:
        notion_token: Notion API token
        db_id: Notion database ID
        data: Dictionary with brief data:
            - request_id: str
            - name: str
            - company: str
            - phone: str
            - email: str
            - locale: str
            - message: str (optional)
    
    Returns:
        Page ID if created successfully, None otherwise
    """
    if not notion_token or not db_id:
        logger.warning("Notion not configured: missing token or db_id")
        return None
    
    try:
        # Run synchronous Notion client in thread pool to avoid blocking
        def _create_page():
            try:
                client = Client(auth=notion_token)
                
                # Build properties according to the schema
                properties = {
                    "Name": {
                        "title": [
                            {
                                "text": {
                                    "content": f"Brief | {data.get('company', 'Unknown')} | {data.get('name', 'Unknown')}"
                                }
                            }
                        ]
                    },
                    "Status": {
                        "status": {
                            "name": "Backlog"
                        }
                    },
                    "Request ID": {
                        "rich_text": [
                            {
                                "text": {
                                    "content": data.get("request_id", "")
                                }
                            }
                        ]
                    },
                    "Email": {
                        "email": data.get("email", "")
                    },
                    "Phone": {
                        "phone_number": data.get("phone", "")
                    },
                    "Locale": {
                        "select": {
                            "name": data.get("locale", "en").upper()
                        }
                    },
                    "Source": {
                        "select": {
                            "name": "Miniapp Brief"
                        }
                    },
                    "Comment": {
                        "rich_text": [
                            {
                                "text": {
                                    "content": data.get("message", "") or ""
                                }
                            }
                        ]
                    },
                }
                
                page = client.pages.create(
                    parent={"database_id": db_id},
                    properties=properties,
                )
                
                return page.get("id", "")
            except APIResponseError as e:
                logger.error(
                    f"Notion API error creating brief page: {e.code} - {e.message} "
                    f"(request_id: {e.request_id})"
                )
                raise
            except Exception as e:
                logger.error(f"Failed to create brief page in Notion: {e}", exc_info=True)
                raise
        
        page_id = await asyncio.to_thread(_create_page)
        logger.info(f"Brief page created in Notion: {page_id}")
        return page_id
        
    except Exception as e:
        logger.error(f"Failed to create brief page in Notion: {e}", exc_info=True)
        return None

