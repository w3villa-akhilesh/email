import logging
import secrets
import re
from typing import Dict
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from database.models import AgentApiKey

logger = logging.getLogger(__name__)

def _slugify(text: str) -> str:
    text = (text or '').strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"(^-|-$)+", "", text)

def _generate_key(client_app_name: str) -> str:
    app = _slugify(client_app_name or 'app')
    rand = secrets.token_hex(24)  # 48 hex chars
    # Format without SR number: w3-<app>-<rand>
    return f"w3-{app}-{rand}"

def create_agent_api_key(db: Session, client_app_name: str) -> Dict:
    """
    Create and persist a unique API key for a client app.
    Returns a dict with the persisted record.
    """
    try:
        # Generate a unique key (retry on extremely rare collision)
        for _ in range(3):
            plaintext_key = _generate_key(client_app_name)
            exists = db.query(AgentApiKey).filter(AgentApiKey.api_key == plaintext_key).first()
            if not exists:
                break
        else:
            raise HTTPException(status_code=500, detail="Failed to generate a unique API key")

        record = AgentApiKey(
            client_app_name=client_app_name,
            api_key=plaintext_key,
            is_active=True,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return {
            "id": record.id,
            "client_app_name": record.client_app_name,
            "api_key": record.api_key,
            "is_active": record.is_active,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"DB error in create_agent_api_key: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating agent API key: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
