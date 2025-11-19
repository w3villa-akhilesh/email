from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
from sqlalchemy.orm import Session
from app.models.db_models import MatchingNotification
from app.services.authenticate_agent import authenticate_invoke_kivo_agent
from app.services.current_user_info import get_current_profile
from app.services.redis_common_state import delete_session_data, get_session_data, save_session_data
from app.services.state_session_manager import list_user_sessions, get_user_session_details, rename_chatname, search_chat_history
from app.services.my_sql_client import get_db
from app.utils.datetime import get_formatted_timestamp
from app.utils.logger import logger
from app.models.schema import MatchingCompletionNotificationPayload, rename_chatname_payload
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.authenticate_agent import get_base_url_from_request
from pm_board_data.core.config import BASE_URL
from app.socket.connect import manager
security = HTTPBearer()
router = APIRouter(prefix="/ats", tags=["ATS Sessions"])

@router.get("/users/sessions")
async def get_list_user_sessions(
    limit: int = Query(default=10, ge=1),
    page: int = Query(default=1, ge=1), 
    credentials: HTTPAuthorizationCredentials = Depends(security),
    base_url: str = Depends(get_base_url_from_request),
    db: Session = Depends(get_db)
):
    """
    Retrieve paginated list of user sessions for ATS functionality.
    
    This endpoint fetches a paginated list of chat sessions belonging to the
    authenticated user, with support for customizing the number of results per page.
    
    Args:
        limit (int): Number of sessions per page (minimum: 1, default: 10)
        page (int): Page number for pagination (minimum: 1, default: 1)
        credentials (HTTPAuthorizationCredentials): Bearer token for authentication
        base_url (str): Base URL extracted from request for authentication
        db (Session): Database session for data access
        
    Returns:
        dict: User sessions with pagination metadata
        
    Raises:
        HTTPException: If authentication fails (403) or required parameters are missing (422)
        
    Example:
        ```json
        {
            "user_id": "user@example.com",
            "sessions": [
                {
                    "session_id": "session_123",
                    "chat_name": "Job Interview Discussion",
                    "created_at": "2024-01-15T10:30:00Z",
                    "last_activity": "2024-01-15T14:45:00Z"
                }
            ]
        }
        ```
    """
    token = credentials.credentials
    profile_info = await get_current_profile(token, BASE_URL)
    profile_info = await get_current_profile(token, BASE_URL)
    if not profile_info or "email" not in profile_info:
        raise HTTPException(status_code=403, detail="Could not validate user credentials.")
    
    user_id = profile_info.get("email")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing required query parameter: user_id"
        )
    logger.info(f"Query param session list request for user_id={user_id}")
    offset = (page - 1) * limit  
    return {
        "user_id": user_id,
        "sessions": list_user_sessions(db, user_id, limit, offset)
    }

# get history 
@router.get("/users/sessions/details")
async def get_session_history(
    session_id: Optional[str] = None,
    limit: int = Query(default=10, ge=1),
    page: int = Query(default=1, ge=1), 
    credentials: HTTPAuthorizationCredentials = Depends(security),
    base_url: str = Depends(get_base_url_from_request),
    db: Session = Depends(get_db)
):
    """
    Retrieve detailed chat history for a specific user session.
    
    This endpoint fetches the detailed conversation history for a given session,
    with support for pagination to handle large conversation histories efficiently.
    The session must belong to the authenticated user.
    
    Args:
        session_id (Optional[str]): Unique identifier of the session (required)
        limit (int): Number of history items per page (minimum: 1, default: 10)
        page (int): Page number for pagination (minimum: 1, default: 1)
        credentials (HTTPAuthorizationCredentials): Bearer token for authentication
        base_url (str): Base URL extracted from request for authentication
        db (Session): Database session for data access
        
    Returns:
        dict: Paginated chat history with conversation details
        
    Raises:
        HTTPException: If authentication fails (403) or required parameters are missing (422)
        
    Example:
        ```json
        {
            "session_id": "session_123",
            "page": 1,
            "limit": 10,
            "total": 25,
            "history": [
                {
                    "event_id": "event_1",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "user_message": "What are the job requirements?",
                    "agent_response": "The job requirements include..."
                }
            ]
        }
        ```
    """
    token = credentials.credentials
    profile_info = await get_current_profile(token, BASE_URL)
    profile_info = await get_current_profile(token, BASE_URL)
    if not profile_info or "email" not in profile_info:
        raise HTTPException(status_code=403, detail="Could not validate user credentials.")
    
    user_id = profile_info.get("email")
    if not user_id or not session_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing required query parameters: user_id and/or session_id"
        )
    
    offset = (page - 1) * limit  
    logger.info(f"Paginated request: user_id={user_id}, session_id={session_id}, limit={limit}, offset={offset}")
    return get_user_session_details(db, user_id, session_id, limit, offset)


@router.get("/users/sessions/search")
async def search_user_chat_history(
    query: str = Query(...),
    limit: int = Query(10, ge=1),
    page: int = Query(default=1, ge=1), 
    credentials: HTTPAuthorizationCredentials = Depends(security),
    base_url: str = Depends(get_base_url_from_request),
    db: Session = Depends(get_db)
):
    """
    Search through user's chat history across all sessions.
    
    This endpoint performs a text-based search through the authenticated user's
    chat history, returning relevant conversations with pagination support.
    The search covers both user messages and agent responses.
    
    Args:
        query (str): Search query string to find in chat history
        limit (int): Number of search results per page (minimum: 1, default: 10)
        page (int): Page number for pagination (minimum: 1, default: 1)
        credentials (HTTPAuthorizationCredentials): Bearer token for authentication
        base_url (str): Base URL extracted from request for authentication
        db (Session): Database session for data access
        
    Returns:
        dict: Paginated search results with matching conversations
        
    Raises:
        HTTPException: If authentication fails (403)
        
    Example:
        ```json
        {
            "query": "Python developer",
            "page": 1,
            "limit": 10,
            "total": 15,
            "results": [
                {
                    "session_id": "session_123",
                    "event_id": "event_5",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "matched_text": "Looking for Python developer with Django experience",
                    "context": "User discussing job requirements..."
                }
            ]
        }
        ```
    """
    token = credentials.credentials
    profile_info = await get_current_profile(token, BASE_URL)
    profile_info = await get_current_profile(token, BASE_URL)
    if not profile_info or "email" not in profile_info:
        raise HTTPException(status_code=403, detail="Could not validate user credentials.")
    
    user_id = profile_info.get("email")
    offset = (page - 1) * limit  
    return search_chat_history(db, user_id, query, limit, offset)


@router.post("/user/sessions/rename_chat")
async def rename_chat_on_sidebar_handler(
    payload: rename_chatname_payload, 
    credentials: HTTPAuthorizationCredentials = Depends(security), 
    db: Session = Depends(get_db), 
    base_url: str = Depends(get_base_url_from_request)
):
    """
    Rename a chat session for better organization in the sidebar.
    
    This endpoint allows users to customize the display name of their chat sessions,
    making it easier to identify and organize conversations in the user interface.
    
    Args:
        payload (rename_chatname_payload): The rename request containing:
            - session_id: Unique identifier of the session to rename
            - chat_name: New display name for the chat session
        credentials (HTTPAuthorizationCredentials): Bearer token for authentication
        db (Session): Database session for data access
        base_url (str): Base URL extracted from request for authentication
        
    Returns:
        dict: Rename operation results and status
        
    Raises:
        HTTPException: If authentication fails (403) or rename operation fails
        
    Example:
        ```json
        {
            "status": "success",
            "message": "Chat renamed successfully",
            "session_id": "session_123",
            "old_name": "Untitled Chat",
            "new_name": "Python Developer Interview"
        }
        ```
    """
    logger.info(f"Invoking rename_chat_on_sidebar_handler endpoint with {base_url}")
    token = credentials.credentials
    profile_info = await get_current_profile(token, BASE_URL)
    profile_info = await get_current_profile(token, BASE_URL)
    if not profile_info or "email" not in profile_info:
        raise HTTPException(status_code=403, detail="Could not validate user credentials.")
    
    user_id = profile_info.get("email")
    return rename_chatname(db, user_id, payload.session_id, payload.chat_name)
 

# endpoint to receive notification of matching job completion.
@router.post("/matching/notification")
async def matching_completion_notification(
    payload: MatchingCompletionNotificationPayload,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Endpoint to handle notifications for custom matching results.
    """
    token = credentials.credentials
    session_id = payload.session_id
    origin = payload.origin
    if not origin:
         raise HTTPException(status_code=302, detail="Could not find origin.")

    profile_info = await get_current_profile(token, origin)
    if not profile_info or "email" not in profile_info:
        raise HTTPException(status_code=403, detail="Could not validate user credentials.")
    
    logger.info(f"Received matching notification from user: {profile_info.get('email')} with payload: {payload}")  
    user_id = profile_info.get("email")
    if payload.status == "success":
        matching_url = f"{origin}/hrms/agent_matching_job_applicants?matching_id={payload.custom_matching_id}"
        notification_message = f"Matching completed successfully. [See results] ({matching_url})"
        session_data = get_session_data(session_id)
        if session_data.get('custom_matching_id'):
            save_session_data(session_id, {"custom_matching_id":""})    
    try:
        notification = MatchingNotification(
            custom_matching_id=payload.custom_matching_id,
            session_id=payload.session_id,
            message=notification_message,
            is_read=False
        )
        db.add(notification)
        db.commit()

        await manager.broadcast_json_to_user(user_id, {
            "action": "batch_completion_notification",
            "session_id": payload.session_id,
            "message_id": payload.custom_matching_id,
            "message": notification_message
        })
        return {"status": "success", "message": "Matching notification saved successfully"}
    
    except Exception as e:
        logger.error(f"Error saving matching result: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save matching result")
    
