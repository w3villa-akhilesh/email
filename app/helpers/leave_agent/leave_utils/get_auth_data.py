from app.services.redis_common_state import get_session_data
from app.utils.logger import logger
from typing import Dict, Any


async def get_session_and_auth_data(session_id: str, app_name: str) -> Dict[str, Any]:
    """
    Helper function to get session data and authentication info.
    
    Returns:
        dict: Contains token, origin, headers, or error information
    """
    session_data = get_session_data(session_id, app_name)
    if not session_data:
        logger.debug("Session data not found, returning error")
        return {"error": "Session data not found. Please try again."}
    
    token = session_data.get("token")
    origin = session_data.get("origin")
    
    if not token or not origin:
        logger.debug("Token or origin missing from session data, returning authentication error")
        return {"error": "Authentication error. Please login again."}
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    return {
        "token": token,
        "origin": origin,
        "headers": headers,
        "session_data": session_data
    }
