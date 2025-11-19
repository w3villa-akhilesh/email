from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from fastapi.responses import JSONResponse
from fastapi import HTTPException
from datetime import datetime

from database.models import Agent, AgentMapping
from services.timezone_utils import to_ist
from logger import logger


def get_agents_data(
    db: Session, 
    name: Optional[str] = None,
    display_name: Optional[str] = None,
    agent_type: Optional[str] = None,
    parent_agent_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 10
):
    """
    Get agents with optional filters and pagination.
    
    Args:
        db: Database session
        name: Filter by agent name (partial match, case-insensitive)
        display_name: Filter by display name (partial match, case-insensitive)
        agent_type: Filter by agent type
        parent_agent_id: Filter by parent agent ID
        is_active: Filter by active status (True/False/None for all)
        page: Page number (starts from 1)
        page_size: Number of items per page
    
    Returns:
        JSONResponse with paginated agents data
    """
    try:
        query = db.query(Agent)
        
        # Apply filters if provided
        if name:
            query = query.filter(Agent.name.ilike(f"%{name}%"))
        
        if display_name:
            query = query.filter(Agent.display_name.ilike(f"%{display_name}%"))
        
        if agent_type:
            query = query.filter(Agent.agent_type == agent_type)
        
        if parent_agent_id is not None:
            query = query.filter(Agent.parent_agent_id == parent_agent_id)
        
        if is_active is not None:
            query = query.filter(Agent.is_active == is_active)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        agents = query.order_by(Agent.created_at.desc()).offset(offset).limit(page_size).all()
        
        # Calculate pagination metadata
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1
        
        agents_data = [
            {
                "id": agent.id,
                "name": agent.name,
                "display_name": agent.display_name,
                "description": agent.description,
                "parent_agent_id": agent.parent_agent_id,
                "agent_type": agent.agent_type,
                "default_model": agent.default_model,
                "system_prompt": agent.system_prompt,
                "capabilities": agent.capabilities,
                "is_active": agent.is_active,
                "created_at": to_ist(agent.created_at) if agent.created_at else None,
                "updated_at": to_ist(agent.updated_at) if agent.updated_at else None
            }
            for agent in agents
        ]
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Retrieved {len(agents_data)} agents (page {page} of {total_pages})",
                "data": agents_data,
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_items": total_count,
                    "total_pages": total_pages,
                    "has_next": has_next,
                    "has_prev": has_prev
                }
            }
        )
    
    except Exception as e:
        logger.error(f"Error getting agents data: {str(e)}")
        raise


def get_agent_by_id_data(db: Session, agent_id: int):
    """
    Get a single agent by ID.
    
    Args:
        db: Database session
        agent_id: Agent ID
    
    Returns:
        JSONResponse with agent data
    """
    try:
        # Find the agent
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "Agent not found"
                }
            )
        
        # Format response data
        agent_data = {
            "id": agent.id,
            "name": agent.name,
            "display_name": agent.display_name,
            "description": agent.description,
            "parent_agent_id": agent.parent_agent_id,
            "agent_type": agent.agent_type,
            "default_model": agent.default_model,
            "system_prompt": agent.system_prompt,
            "capabilities": agent.capabilities,
            "is_active": agent.is_active,
            "created_at": to_ist(agent.created_at) if agent.created_at else None,
            "updated_at": to_ist(agent.updated_at) if agent.updated_at else None
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Agent retrieved successfully",
                "data": agent_data
            }
        )
    
    except Exception as e:
        logger.error(f"Error getting agent {agent_id}: {str(e)}")
        raise


def create_agent_data(db: Session, agent_data: Dict[str, Any]):
    """
    Create a new agent.
    
    Args:
        db: Database session
        agent_data: Agent data dictionary
    
    Returns:
        JSONResponse with created agent data
    """
    try:
        # Check if agent with same name already exists
        existing_agent = db.query(Agent).filter(Agent.name == agent_data["name"]).first()
        if existing_agent:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": f"Agent with name '{agent_data['name']}' already exists"
                }
            )
        
        # Validate parent_agent_id if provided
        if agent_data.get("parent_agent_id"):
            parent_agent = db.query(Agent).filter(Agent.id == agent_data["parent_agent_id"]).first()
            if not parent_agent:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": f"Parent agent with ID {agent_data['parent_agent_id']} does not exist"
                    }
                )
        
        # Create new agent
        agent = Agent(
            name=agent_data["name"],
            display_name=agent_data["display_name"],
            description=agent_data.get("description"),
            parent_agent_id=agent_data.get("parent_agent_id"),
            agent_type=agent_data.get("agent_type", "primary"),
            default_model=agent_data.get("default_model"),
            system_prompt=agent_data.get("system_prompt"),
            capabilities=agent_data.get("capabilities"),
            is_active=agent_data.get("is_active", True)
        )
        
        db.add(agent)
        db.commit()
        db.refresh(agent)
        
        # Format response data
        created_agent = {
            "id": agent.id,
            "name": agent.name,
            "display_name": agent.display_name,
            "description": agent.description,
            "parent_agent_id": agent.parent_agent_id,
            "agent_type": agent.agent_type,
            "default_model": agent.default_model,
            "system_prompt": agent.system_prompt,
            "capabilities": agent.capabilities,
            "is_active": agent.is_active,
            "created_at": to_ist(agent.created_at) if agent.created_at else None,
            "updated_at": to_ist(agent.updated_at) if agent.updated_at else None
        }
        
        return JSONResponse(
            status_code=201,
            content={
                "status": "success",
                "message": "Agent created successfully",
                "data": created_agent
            }
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating agent: {str(e)}")
        raise


def update_agent_data(db: Session, agent_id: int, update_data: Dict[str, Any]):
    """
    Update an agent by ID.
    
    Args:
        db: Database session
        agent_id: Agent ID
        update_data: Data to update
    
    Returns:
        JSONResponse with updated agent data
    """
    try:
        # Find the agent
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "Agent not found"
                }
            )
        
        # Check if name is being updated and if it conflicts with existing agent
        if "name" in update_data and update_data["name"] != agent.name:
            existing_agent = db.query(Agent).filter(
                Agent.name == update_data["name"],
                Agent.id != agent_id
            ).first()
            if existing_agent:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": f"Agent with name '{update_data['name']}' already exists"
                    }
                )
        
        # Validate parent_agent_id if being updated
        if "parent_agent_id" in update_data and update_data["parent_agent_id"]:
            if update_data["parent_agent_id"] == agent_id:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": "Agent cannot be its own parent"
                    }
                )
            parent_agent = db.query(Agent).filter(Agent.id == update_data["parent_agent_id"]).first()
            if not parent_agent:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": f"Parent agent with ID {update_data['parent_agent_id']} does not exist"
                    }
                )
        
        # Update fields
        for key, value in update_data.items():
            if hasattr(agent, key):
                setattr(agent, key, value)
        
        agent.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(agent)
        
        # Format response data
        updated_agent = {
            "id": agent.id,
            "name": agent.name,
            "display_name": agent.display_name,
            "description": agent.description,
            "parent_agent_id": agent.parent_agent_id,
            "agent_type": agent.agent_type,
            "default_model": agent.default_model,
            "system_prompt": agent.system_prompt,
            "capabilities": agent.capabilities,
            "is_active": agent.is_active,
            "created_at": to_ist(agent.created_at) if agent.created_at else None,
            "updated_at": to_ist(agent.updated_at) if agent.updated_at else None
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Agent updated successfully",
                "data": updated_agent
            }
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating agent {agent_id}: {str(e)}")
        raise


def delete_agent_data(db: Session, agent_id: int):
    """
    Delete an agent by ID with relationship integrity checks.
    
    Args:
        db: Database session
        agent_id: Agent ID
    
    Returns:
        JSONResponse with deletion status
    """
    try:
        # Find the agent
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "Agent not found"
                }
            )
        
        # Check for dependent records
        agent_mappings_count = db.query(AgentMapping).filter(AgentMapping.agent_id == agent_id).count()
        child_agents_count = db.query(Agent).filter(Agent.parent_agent_id == agent_id).count()
        
        if agent_mappings_count > 0 or child_agents_count > 0:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": f"Cannot delete agent. It has {agent_mappings_count} agent mappings and {child_agents_count} child agents associated with it. Please remove these dependencies first."
                }
            )
        
        # Safe to delete - no dependencies
        db.delete(agent)
        db.commit()
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Agent deleted successfully"
            }
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting agent {agent_id}: {str(e)}")
        raise


def toggle_agent_status_data(db: Session, agent_id: int):
    """
    Toggle the active status of an agent.
    
    Args:
        db: Database session
        agent_id: Agent ID
    
    Returns:
        JSONResponse with updated agent data
    """
    try:
        # Find the agent
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "Agent not found"
                }
            )
        
        # Toggle the status
        agent.is_active = not agent.is_active
        agent.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(agent)
        
        # Format response data
        updated_agent = {
            "id": agent.id,
            "name": agent.name,
            "display_name": agent.display_name,
            "description": agent.description,
            "parent_agent_id": agent.parent_agent_id,
            "agent_type": agent.agent_type,
            "default_model": agent.default_model,
            "system_prompt": agent.system_prompt,
            "capabilities": agent.capabilities,
            "is_active": agent.is_active,
            "created_at": to_ist(agent.created_at) if agent.created_at else None,
            "updated_at": to_ist(agent.updated_at) if agent.updated_at else None
        }
        
        status_text = "activated" if agent.is_active else "deactivated"
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Agent {status_text} successfully",
                "data": updated_agent
            }
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error toggling agent status {agent_id}: {str(e)}")
        raise

