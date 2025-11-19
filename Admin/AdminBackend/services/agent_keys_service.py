import logging
from typing import Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from database.models import AgentApiKey
from .timezone_utils import to_ist

logger = logging.getLogger(__name__)

def get_agent_keys_list(
    db: Session,
    app_name: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> Dict:
    try:
        query = db.query(AgentApiKey)

        if app_name:
            query = query.filter(AgentApiKey.client_app_name.like(f"%{app_name}%"))

        if status:
            if status.lower() == 'active':
                query = query.filter(AgentApiKey.is_active == True)
            elif status.lower() == 'inactive':
                query = query.filter(AgentApiKey.is_active == False)

        total = query.count()
        offset = (page - 1) * page_size
        records = query.order_by(AgentApiKey.created_at.desc()).offset(offset).limit(page_size).all()
        
        data = []
        for rec in records:
            data.append({
                'id': rec.id,
                'client_app_name': rec.client_app_name,
                'api_key': rec.api_key,  # encrypted
                'is_active': rec.is_active,
                'created_at': to_ist(rec.created_at) if rec.created_at else None,
                'updated_at': to_ist(rec.updated_at) if rec.updated_at else None,
            })

        total_pages = (total + page_size - 1) // page_size

        return {
            'data': data,
            'page': page,
            'page_size': page_size,
            'total_count': total,
            'total_pages': total_pages,
            'filters': {
                'app_name': app_name,
                'status': status,
            },
        }
    except SQLAlchemyError as e:
        logger.error(f"DB error in get_agent_keys_list: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Error fetching agent keys list: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def delete_agent_key(db: Session, key_id: int) -> bool:
    """Hard delete an agent API key by ID."""
    try:
        rec = db.query(AgentApiKey).filter(AgentApiKey.id == key_id).first()
        if not rec:
            return False
        db.delete(rec)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"DB error in delete_agent_key: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting agent key: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
