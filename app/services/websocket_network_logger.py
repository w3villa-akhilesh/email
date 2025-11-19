"""
WebSocket Network Activity Logger

This module provides helper functions to log network activity for WebSocket connections.
Since WebSockets don't work with the standard FastAPI dependency injection,
this provides a simplified logging approach for WebSocket endpoints.
"""

from fastapi import WebSocket
from sqlalchemy.orm import Session
from app.services.network_activity_logger import NetworkActivityLogger
from app.services.my_sql_client import SessionLocal
from app.utils.logger import logger
from typing import Optional


async def log_websocket_connection(
    websocket: WebSocket,
    endpoint: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    company_id: Optional[str] = None,
):
    """
    Log WebSocket connection establishment.
    
    This function logs the initial WebSocket connection with network details.
    It creates a database session, logs the activity, and closes the session.
    
    Args:
        websocket: FastAPI WebSocket object
        endpoint: WebSocket endpoint path (e.g., "/ws/invoke-iats-agent")
        user_id: User identifier (email) if authenticated
        session_id: Session identifier if available
        company_id: Company identifier if available
    """
    db: Session = SessionLocal()
    try:
        # Create a mock request-like object from WebSocket
        class WebSocketRequest:
            def __init__(self, ws: WebSocket):
                self.url = type('obj', (object,), {'path': endpoint})()
                self.method = "WEBSOCKET"
                self.headers = ws.headers
                self.client = ws.client
        
        mock_request = WebSocketRequest(websocket)
        
        # Log the connection
        NetworkActivityLogger.log_activity(
            request=mock_request,
            db=db,
            user_id=user_id,
            session_id=session_id,
            company_id=company_id,
            status_code=101,  # 101 Switching Protocols (WebSocket)
        )
        
        logger.debug(f"WebSocket connection logged: endpoint={endpoint}, user_id={user_id}")
        
    except Exception as e:
        logger.error(f"Failed to log WebSocket connection: {str(e)}", exc_info=True)
    finally:
        db.close()


async def log_websocket_message(
    websocket: WebSocket,
    endpoint: str,
    action: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    company_id: Optional[str] = None,
):
    """
    Log WebSocket message activity.
    
    This function logs individual WebSocket messages/actions.
    Use this for significant actions like agent invocations.
    
    Args:
        websocket: FastAPI WebSocket object
        endpoint: WebSocket endpoint path with action (e.g., "/ws/invoke-iats-agent?action=invoke_agent")
        action: The action being performed (e.g., "invoke_agent", "get_sessions")
        user_id: User identifier (email) if authenticated
        session_id: Session identifier if available
        company_id: Company identifier if available
    """
    db: Session = SessionLocal()
    try:
        # Create endpoint path with action
        full_endpoint = f"{endpoint}?action={action}"
        
        # Create a mock request-like object from WebSocket
        class WebSocketRequest:
            def __init__(self, ws: WebSocket, path: str):
                self.url = type('obj', (object,), {'path': path})()
                self.method = "WS_MESSAGE"
                self.headers = ws.headers
                self.client = ws.client
        
        mock_request = WebSocketRequest(websocket, full_endpoint)
        
        # Log the message
        NetworkActivityLogger.log_activity(
            request=mock_request,
            db=db,
            user_id=user_id,
            session_id=session_id,
            company_id=company_id,
            status_code=200,  # Success
        )
        
        logger.debug(f"WebSocket message logged: endpoint={full_endpoint}, user_id={user_id}")
        
    except Exception as e:
        logger.error(f"Failed to log WebSocket message: {str(e)}", exc_info=True)
    finally:
        db.close()

