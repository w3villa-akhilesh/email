from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from database.models import Event
from fastapi import HTTPException
from sqlalchemy import desc
from services.timezone_utils import to_ist
from logger import logger

def summarize_event_content_types(db: Session, id: str):
    try:
        event_data = db.query(Event).filter(Event.id == id) \
            .order_by(desc(Event.timestamp)).all()

        if not event_data:
            raise HTTPException(status_code=404, detail="No events found for the given session_id")

        content_types = []
        for event in event_data:
            try:
                content = event.content or {}
                parts = content.get("parts", [])

                if not isinstance(parts, list):
                  continue  # Skip this event if 'parts' is not a list

                for part in parts:
                    if isinstance(part, dict):
                       content_types.extend(part.keys())
            except Exception:
              continue  # Skip this event on any unexpected issue

        # Return unique types only
        return list(set(content_types))

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing event content: {str(e)}")


def get_event_data(db: Session, session_id: str, page: int = 1, page_size: int = 15):
    try:
        # Handle URL encoding: + becomes space in URL decoding, restore it
        session_id = session_id.strip().replace(" ", "+")
        
        # Calculate offset and limit
        offset = (page - 1) * page_size
        
        # Fetch events sorted by timestamp in descending order with pagination
        event_data_query = db.query(Event).filter(Event.session_id == session_id) \
            .order_by(desc(Event.timestamp))

        # Get total count for pagination metadata
        total_count = event_data_query.count()
        
        # Apply pagination (limit and offset)
        event_data = event_data_query.offset(offset).limit(page_size).all()

        if not event_data:
            raise HTTPException(status_code=404, detail="No events found for the given session_id")

        # Format the response to match the desired structure
        formatted_data = []
        for event in event_data:
            ts_ist = to_ist(event.timestamp)
            event_info = {
                "session_id": event.session_id,
                "id": event.id,
                "timestamp": ts_ist,
                "author": event.author,
                "app_name": event.app_name,
                "call_type": summarize_event_content_types(db, event.id)
            }
            formatted_data.append(event_info)

        # Calculate total pages based on total count and page size
        total_pages = (total_count + page_size - 1) // page_size  # Ceiling division

        # Return paginated data and metadata
        return {
            "data": formatted_data,
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages
        }

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Error fetching event data: {str(e)}")
