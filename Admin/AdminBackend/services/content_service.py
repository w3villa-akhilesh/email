from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import desc
from database.models import Event
from fastapi import HTTPException
from services.timezone_utils import to_ist
from logger import logger

def get_event_content(db: Session, event_id: int = None, session_id: str = None):
    try:
        # If event_id is provided, fetch the specific event
        if event_id:
            event = db.query(Event).filter(Event.id == event_id).first()

            if not event:
                raise HTTPException(status_code=404, detail="Event not found")

            # Return content of the specific event
            ts_ist = to_ist(event.timestamp)
            event_info = {
                "id": event.id,
                "timestamp": ts_ist,
                "author": event.author,
                "content": event.content
            }
            return event_info

        # If no event_id is provided, fetch all events for the given session_id
        if session_id:
            # Handle URL encoding: + becomes space in URL decoding, restore it
            session_id = session_id.strip().replace(" ", "+")
            # Use exact match for session_id to avoid matching multiple sessions
            events = db.query(Event).filter(Event.session_id == session_id) \
                .order_by(desc(Event.timestamp)).all()

            if not events:
                raise HTTPException(status_code=404, detail="No events found for the given session_id")

            all_events_info = []
            for event in events:
                if event.content:  # Ensure only events with content are returned
                    ts_ist = to_ist(event.timestamp)
                    event_info = {
                        "id": event.id,
                        "timestamp": ts_ist,
                        "author": event.author,
                        "content": event.content
                    }
                    all_events_info.append(event_info)

            if not all_events_info:
                raise HTTPException(status_code=404, detail="No content available for the events")

            return all_events_info

        # If neither event_id nor session_id is provided, raise an error
        raise HTTPException(status_code=400, detail="Either event_id or session_id must be provided")

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Error fetching event content: {str(e)}")
