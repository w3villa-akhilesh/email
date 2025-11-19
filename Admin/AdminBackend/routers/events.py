from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import distinct
from typing import Optional

from database.connection import get_db
from database.models import Event
from services.session_detail import get_event_data
from services.content_service import get_event_content
from services.log_service import count_sessions
from routers.auth import validate_token, get_token
from logger import logger

router = APIRouter(tags=["events"])

@router.get("/events/{session_id}")
def get_paginated_event_data(
    session_id: str, 
    access_token: str = Depends(get_token), 
    db: Session = Depends(get_db), 
    page: int = 1, 
    page_size: int = 15
):
    """
    Fetch paginated event data for a given session_id.
    Requires a valid access token.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        
        return get_event_data(db, session_id, page, page_size)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_paginated_event_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/event/content")
def get_event_content_query(
    event_id: str = None, 
    session_id: str = None, 
    access_token: str = Depends(get_token), 
    db: Session = Depends(get_db)
):
    """
    Fetch content for a specific event by event_id or fetch all events by session_id.
    Either event_id or session_id must be provided.
    Requires a valid access token.
    """
    try:
        # Validate the access token
        validate_token(access_token)

        return get_event_content(db, event_id=event_id, session_id=session_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_event_content_query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/session_counts")
def get_session_counts(
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    email: Optional[str] = Query(None, min_length=0, max_length=255),
    date_from: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD format)"),
    date_to: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD format)"),
    app_name: Optional[str] = Query(None, description="Optional app name to filter by"),
    session_id: Optional[str] = Query(None, description="Optional session_id to filter by"),
    mode: Optional[str] = Query(None, description="Optional mode to filter by")
):
    """
    Fetch session counts for optionally specified app, with filters:
    - date_from and date_to (range)
    - email (optional; if not given, return all sessions)
    - app_name (optional; if not given, return all sessions)
    - session_id (optional; if not given, return all sessions)
    """

    try:
        # Validate the access token
        validate_token(access_token)

        session_counts = count_sessions(db, app_name, email, date_from, date_to, page, page_size, session_id, mode)

        if isinstance(session_counts, str) and (session_counts.startswith("Failed") or session_counts == "No session data found"):
            raise HTTPException(status_code=404, detail=session_counts)

        return JSONResponse(content=session_counts)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in session_counts endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/available_app_names")
def get_available_app_names(
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    """
    Return unique app names from the events table.
    Requires a valid access token.
    """
    try:
        # Token validation
        validate_token(access_token)

        # Query unique app names from Event table
        app_names_query = db.query(distinct(Event.app_name)).all()

        # Flatten the result (it's a list of tuples)
        app_names = [row[0] for row in app_names_query if row[0] is not None]

        return JSONResponse(content={"app_names": app_names})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /available_app_names: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
