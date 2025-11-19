from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
from typing import Optional

from database.connection import get_db
from database.models import User
from routers.auth import get_token
from logger import logger


def get_current_user(
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
) -> Optional[int]:
    """
    Get current user ID from access token.
    
    Args:
        access_token: Bearer token from request
        db: Database session
    
    Returns:
        User ID if found, None otherwise
    """
    try:
        # Find user by access token
        user = db.query(User).filter(User.access_token == access_token).first()
        if user:
            return user.id
        else:
            logger.warning(f"No user found for access token: {access_token[:10]}...")
            return None
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        return None


