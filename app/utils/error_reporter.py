"""
Utility functions for standardized error reporting across agents.
"""
from typing import List, Dict, Optional, Any
from app.services.email_notifier import send_exception_email
from app.utils.logger import logger


def report_agent_initialization_errors(
    errors: List[Dict[str, Any]],
    session_id: str,
    origin: str,
    company_id: str,
    context: str,
    query: Optional[str] = None
) -> None:
    """
    Reports agent initialization errors in a standardized format.
    
    Args:
        errors: List of error dictionaries containing 'agent' and 'error' keys
        session_id: Session identifier
        origin: Origin of the request
        company_id: Company identifier
        context: Context description (e.g., "safe_run_agent", "safe_run_agents")
        query: Optional query string to include in error details
    """
    if not errors:
        return
    
    # Format the base error message
    error_message = "\n".join(str(e) for e in errors)
    error_details = f"{error_message}\nSession ID: {session_id}\nOrigin: {origin}\nCompany ID: {company_id}"
    
    # Add query if provided
    if query:
        error_details = f"{error_message}\nSession ID: {session_id}\nQuery: {query}\nOrigin: {origin}\nCompany ID: {company_id}"
    
    # Send exception email
    send_exception_email(
        Exception(error_details),
        f"Error initializing agents in {context}:\n{error_details}",
        session_id=session_id,
        origin=origin,
        company_id=company_id
    )
    
    logger.error(f"Agent initialization errors in {context}: {error_details}")
