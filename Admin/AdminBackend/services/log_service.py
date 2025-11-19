from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from database.models import Event, SessionMode
from sqlalchemy import func
from fastapi import HTTPException
from datetime import datetime
from typing import Optional
from services.timezone_utils import to_ist_range
from logger import logger

def count_sessions(
    db: Session,
    app_name: Optional[str] = None,
    email: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    session_id: Optional[str] = None,
    mode: Optional[str] = None 
):
    """
    Counts occurrences of each session_id with optional filters:
    app_name, email (partial match), date range, and session_id (partial match), mode.
    Supports pagination.
    """
    try:
        offset = (page - 1) * page_size

        # Base query with join to session mode table
        session_counts_query = db.query(
            Event.app_name,
            Event.session_id,
            Event.user_id,
            func.count(Event.session_id),
            func.min(Event.timestamp).label('first_timestamp'),
            func.max(Event.timestamp).label('last_timestamp'),
            SessionMode.mode
        ).join(SessionMode, SessionMode.session_id == Event.session_id, isouter=True)

        # Apply filters if provided
        if app_name:
            session_counts_query = session_counts_query.filter(Event.app_name == app_name)

        if email:
            session_counts_query = session_counts_query.filter(Event.user_id.ilike(f"%{email}%"))

        if session_id:
            session_id = session_id.strip().replace(" ", "+")
            session_counts_query = session_counts_query.filter(Event.session_id.ilike(f"%{session_id}%"))
        
        if mode: 
            session_counts_query = session_counts_query.filter(SessionMode.mode.ilike(f"%{mode}%"))

        if date_from:
            try:
                from_datetime = datetime.strptime(date_from, '%Y-%m-%d')
                session_counts_query = session_counts_query.filter(Event.timestamp >= from_datetime)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_from format. Use YYYY-MM-DD")

        if date_to:
            try:
                to_datetime = datetime.strptime(date_to, '%Y-%m-%d')
                to_datetime = to_datetime.replace(hour=23, minute=59, second=59, microsecond=999999)
                session_counts_query = session_counts_query.filter(Event.timestamp <= to_datetime)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_to format. Use YYYY-MM-DD")

        if date_from and date_to:
            if datetime.strptime(date_from, '%Y-%m-%d') > datetime.strptime(date_to, '%Y-%m-%d'):
                raise HTTPException(status_code=400, detail="date_from cannot be later than date_to")

        # Group by including mode
        session_counts_query = session_counts_query.group_by(
            Event.app_name, Event.session_id, Event.user_id, SessionMode.mode
        )
        session_counts_query = session_counts_query.order_by(func.max(Event.timestamp).desc())
        total_count = session_counts_query.count()

        session_counts = session_counts_query.offset(offset).limit(page_size).all()

        if not session_counts:
            return {
                "message": "No session data found for the specified criteria",
                "data": [],
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "filters": {
                    "app_name": app_name,
                    "email": email,
                    "date_from": date_from,
                    "date_to": date_to,
                    "session_id": session_id,
                    "mode": mode
                }
            }

        session_data = []
        for rec_app, session_id_val, user_id, count, first_ts, last_ts, mode in session_counts:
            first_ts_ist, last_ts_ist = to_ist_range(first_ts, last_ts)
            session_data.append({
                "app_name": rec_app,
                "session_id": session_id_val,
                "user_id": user_id,
                "count": count,
                "first_timestamp": first_ts_ist,
                "last_timestamp": last_ts_ist,
                "mode": mode
            })

        total_pages = (total_count + page_size - 1) // page_size

        return {
            "data": session_data,
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages,
            "filters": {
                "app_name": app_name,
                "email": email,
                "date_from": date_from,
                "date_to": date_to,
                "session_id": session_id,
                "mode": mode
            }
        }

    except SQLAlchemyError as e:
        logger.error(f"DB error in count_sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
