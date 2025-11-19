from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional

from database.connection import get_db
from services.agent_service import (
    get_agents_data, 
    get_agent_by_id_data, 
    create_agent_data, 
    update_agent_data, 
    delete_agent_data, 
    toggle_agent_status_data
)
from schemas import AgentCreate, AgentUpdate
from routers.auth import validate_token, get_token
from logger import logger

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("")
def agents_data(
    name: Optional[str] = Query(None, description="Search by agent name (partial match, case-insensitive)"),
    display_name: Optional[str] = Query(None, description="Search by display name (partial match, case-insensitive)"),
    agent_type: Optional[str] = Query(None, description="Filter by agent type (primary, sub_agent, tool)"),
    parent_agent_id: Optional[int] = Query(None, description="Filter by parent agent ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status (true/false, omit for all)"),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page (1-100)"),
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    """
    Get all agents with optional search filters and pagination.
    
    Search Parameters:
    - name: Search agents by name (partial match, case-insensitive)
    - display_name: Search agents by display name (partial match, case-insensitive)
    - agent_type: Filter by agent type (primary, sub_agent, tool)
    - parent_agent_id: Filter by parent agent ID
    - is_active: Filter by active status (true for active, false for inactive, omit for all)
    - page: Page number (starts from 1)
    - page_size: Number of items per page (1-100)
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        return get_agents_data(
            db, 
            name=name,
            display_name=display_name,
            agent_type=agent_type,
            parent_agent_id=parent_agent_id, 
            is_active=is_active, 
            page=page, 
            page_size=page_size
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in agents_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{agent_id}")
def get_agent_by_id(
    agent_id: int,
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    """
    Get a single agent by ID.
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        return get_agent_by_id_data(db, agent_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_agent_by_id: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("")
def create_agent(
    agent: AgentCreate,
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    """
    Create a new agent.
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        return create_agent_data(db, agent.dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.put("/{agent_id}")
def update_agent(
    agent_id: int,
    agent_update: AgentUpdate,
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    """
    Update an agent by ID.
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        # Only include fields that were actually provided
        update_data = agent_update.dict(exclude_unset=True)
        return update_agent_data(db, agent_id, update_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/{agent_id}")
def delete_agent(
    agent_id: int,
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    """
    Delete an agent by ID.
    
    This will check for dependent records (AgentMappings and child agents) 
    and prevent deletion if dependencies exist to maintain referential integrity.
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        return delete_agent_data(db, agent_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.put("/{agent_id}/toggle-status")
def toggle_agent_status(
    agent_id: int,
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    """
    Toggle the active status of an agent (active <-> inactive).
    
    This endpoint switches the is_active field between True and False.
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        return toggle_agent_status_data(db, agent_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in toggle_agent_status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

