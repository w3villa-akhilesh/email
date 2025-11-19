"""
FastAPI Dependency for Network Activity Logging

This module provides FastAPI dependencies that automatically capture and log
network activity details for all endpoints that include the dependency.
"""

from typing import Optional, Dict, Any
from fastapi import Request, Depends
from sqlalchemy.orm import Session
from app.services.my_sql_client import get_db
from app.services.network_activity_logger import NetworkActivityLogger, UserAgentParser
from app.models.db_models import NetworkActivityLog
from app.utils.logger import logger


class NetworkActivityContext:
    """
    Context object that holds network activity information and provides
    methods to update it during request processing.
    """
    
    def __init__(self, request: Request, db: Session):
        self.request = request
        self.db = db
        self.user_id: Optional[str] = None
        self.session_id: Optional[str] = None
        self.company_id: Optional[str] = None
        self.status_code: Optional[int] = None
        self._log_entry: Optional[NetworkActivityLog] = None
        self._logged = False
    
    def set_user_id(self, user_id: str):
        """Set the user ID for this request."""
        self.user_id = user_id
    
    def set_session_id(self, session_id: str):
        """Set the session ID for this request."""
        self.session_id = session_id
    
    def set_company_id(self, company_id: str):
        """Set the company ID for this request."""
        self.company_id = company_id
    
    def set_status_code(self, status_code: int):
        """Set the response status code for this request."""
        self.status_code = status_code
    
    def log_now(self) -> Optional[NetworkActivityLog]:
        """
        Immediately log the network activity with current context.
        
        Returns:
            NetworkActivityLog instance if successful, None otherwise
        """
        if self._logged:
            logger.debug("Network activity already logged for this request")
            return self._log_entry
        
        self._log_entry = NetworkActivityLogger.log_activity(
            request=self.request,
            db=self.db,
            user_id=self.user_id,
            session_id=self.session_id,
            company_id=self.company_id,
            status_code=self.status_code
        )
        self._logged = True
        return self._log_entry
    
    async def log_now_async(self) -> Optional[NetworkActivityLog]:
        """
        Async version of log_now.
        
        Returns:
            NetworkActivityLog instance if successful, None otherwise
        """
        return self.log_now()


async def log_network_activity_dependency(
    request: Request,
    db: Session = Depends(get_db)
) -> NetworkActivityContext:
    """
    FastAPI dependency that logs network activity immediately upon request.
    
    This dependency should be used at the endpoint level to automatically
    capture network activity details as soon as the endpoint is hit.
    
    Usage:
        @app.post("/my-endpoint")
        async def my_endpoint(
            network_logger: NetworkActivityContext = Depends(log_network_activity_dependency)
        ):
            # Network activity is already logged
            # Optionally update context later:
            network_logger.set_user_id("user123")
            network_logger.set_company_id("company456")
            # No need to call log_now() again unless you want to update
            ...
    
    Args:
        request: FastAPI Request object
        db: SQLAlchemy database session
        
    Returns:
        NetworkActivityContext instance
    """
    context = NetworkActivityContext(request, db)
    # Log immediately when the dependency is called
    context.log_now()
    return context


async def get_network_activity_context(
    request: Request,
    db: Session = Depends(get_db)
) -> NetworkActivityContext:
    """
    FastAPI dependency that provides a context for logging network activity.
    
    Unlike log_network_activity_dependency, this does NOT log immediately.
    Instead, it provides a context object that can be updated with user/session
    information and then explicitly logged by calling log_now().
    
    This is useful when you need to gather authentication information before logging.
    
    Usage:
        @app.post("/my-endpoint")
        async def my_endpoint(
            network_ctx: NetworkActivityContext = Depends(get_network_activity_context)
        ):
            # Log immediately at the start
            network_ctx.log_now()
            
            # ... do authentication ...
            network_ctx.set_user_id("user123")
            network_ctx.set_company_id("company456")
            # Context is already logged, updates won't be saved
            # unless you need to log again with updated info
            ...
    
    Args:
        request: FastAPI Request object
        db: SQLAlchemy database session
        
    Returns:
        NetworkActivityContext instance (not yet logged)
    """
    return NetworkActivityContext(request, db)


# Simple function-based dependency for immediate logging without context
async def log_network_activity_simple(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Simple dependency that logs network activity immediately with minimal overhead.
    
    Use this when you just want to log the request without any additional context
    or updates. This is the simplest way to add logging to an endpoint.
    
    Usage:
        @app.post("/my-endpoint")
        async def my_endpoint(
            _: None = Depends(log_network_activity_simple)
        ):
            # Network activity has been logged
            ...
    
    Args:
        request: FastAPI Request object
        db: SQLAlchemy database session
    """
    NetworkActivityLogger.log_activity(
        request=request,
        db=db,
        user_id=None,
        session_id=None,
        company_id=None,
        status_code=None
    )


def extract_network_details_from_request(request: Request) -> Dict[str, Any]:
    """
    Extract network details from a FastAPI request for error reporting.
    
    This is a lightweight function to get network details without database logging.
    Useful for including network context in error emails.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Dict with network details (ip_address, device_type, browser, os, user_agent)
    """
    try:
        # Extract IP address
        ip_address = None
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            ip_address = forwarded_for.split(',')[0].strip()
        elif request.client:
            ip_address = request.client.host
        
        # Parse user agent
        user_agent = request.headers.get('user-agent', '')
        parsed_ua = UserAgentParser.parse(user_agent)
        
        return {
            'ip_address': ip_address,
            'device_type': parsed_ua.get('device_type'),
            'browser': parsed_ua.get('browser'),
            'browser_version': parsed_ua.get('browser_version'),
            'os': parsed_ua.get('os'),
            'os_version': parsed_ua.get('os_version'),
            'user_agent': user_agent[:200] if user_agent else None,  # Truncate for email
        }
    except Exception as e:
        logger.error(f"Error extracting network details: {str(e)}")
        return {}

