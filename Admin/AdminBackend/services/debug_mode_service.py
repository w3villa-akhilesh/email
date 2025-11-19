from sqlalchemy.orm import Session
from sqlalchemy import desc, func, distinct
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from database.models import Event, SessionMode
from services.timezone_utils import to_ist

# Configure logger
logger = logging.getLogger(__name__)


def get_session_list(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    session_id: Optional[str] = None,
    app_name: Optional[str] = None,
    user_id: Optional[str] = None,
    author: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get paginated list of sessions with filtering.
    Returns unique sessions with their metadata.
    """
    try:
        # Build query with SessionMode join (matching Worklog logic)
        query = db.query(
            Event.session_id,
            Event.app_name,
            Event.user_id,
            func.min(Event.timestamp).label('first_event'),
            func.max(Event.timestamp).label('last_event'),
            func.count(Event.id).label('event_count'),
            func.count(distinct(Event.author)).label('agent_count'),
            SessionMode.mode
        ).join(SessionMode, SessionMode.session_id == Event.session_id, isouter=True)
        
        # Apply filters
        if session_id:
            # Handle URL encoding: + becomes space in URL decoding, restore it
            session_id = session_id.strip().replace(" ", "+")
            # Use exact match for session_id to avoid matching multiple sessions
            query = query.filter(Event.session_id == session_id)
        
        if app_name:
            query = query.filter(Event.app_name == app_name)
        
        if user_id:
            # Use ilike for case-insensitive search (matching Worklog logic)
            query = query.filter(Event.user_id.ilike(f"%{user_id}%"))
        
        if author:
            # Filter by author with case-insensitive search
            query = query.filter(Event.author.ilike(f"%{author}%"))
        
        if date_from:
            try:
                date_from_dt = datetime.strptime(date_from, "%Y-%m-%d")
                query = query.filter(Event.timestamp >= date_from_dt)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_dt = datetime.strptime(date_to, "%Y-%m-%d")
                # Add one day to include the entire end date (matching Worklog logic)
                date_to_dt = date_to_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
                query = query.filter(Event.timestamp <= date_to_dt)
            except ValueError:
                pass
        
        # Group by including mode (matching Worklog logic)
        query = query.group_by(
            Event.app_name,
            Event.session_id,
            Event.user_id,
            SessionMode.mode
        )
        
        # Order by latest activity
        query = query.order_by(desc('last_event'))
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        sessions = query.offset(offset).limit(page_size).all()
        
        # Format results (mode is now included in query results)
        formatted_sessions = []
        for session in sessions:
            formatted_sessions.append({
                "session_id": session.session_id,
                "app_name": session.app_name,
                "user_id": session.user_id,
                "mode": session.mode,  # Now from JOIN, not separate query
                "first_event": to_ist(session.first_event) if session.first_event else None,
                "last_event": to_ist(session.last_event) if session.last_event else None,
                "event_count": session.event_count,
                "agent_count": session.agent_count
            })
        
        total_pages = (total_count + page_size - 1) // page_size
        
        return {
            "sessions": formatted_sessions,
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages
        }
    
    except SQLAlchemyError as e:
        logger.error(f"Error in get_session_list: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
