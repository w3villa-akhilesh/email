from sqlalchemy.orm import Session, selectinload
from typing import Optional, Dict, Any, List
from fastapi.responses import JSONResponse
from fastapi import HTTPException
from datetime import datetime

from database.models import AgentMapping, Agent, Company, LLMCredentials
from services.timezone_utils import to_ist
from services.cache_invalidation_service import cache_invalidation_service
from logger import logger


def get_company_agent_mappings_hierarchy(db: Session, company_id: int, page: int = 1, page_size: int = 10):
    """
    Get all agent mappings for a company organized in a hierarchical structure with pagination.
    This will show agents in a tree structure with parent-child relationships.
    Pagination is applied at the root agent level (agents with no parent).
    
    Args:
        db: Database session
        company_id: Company ID
        page: Page number (starts from 1)
        page_size: Number of root agents per page
    
    Returns:
        JSONResponse with hierarchical agent mappings data
    """
    try:
        # Verify company exists
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "Company not found"
                }
            )
        
        # Get all agents (without relationships first to build our own structure)
        all_agents = db.query(Agent).all()
        
        # Get all agent mappings for this company
        agent_mappings = db.query(AgentMapping).filter(
            AgentMapping.company_id == company_id
        ).all()
        
        # Create a mapping dictionary for quick lookup
        mapping_dict = {mapping.agent_id: mapping for mapping in agent_mappings}
        
        # Create a dictionary of all agents by ID for quick lookup
        agents_by_id = {agent.id: agent for agent in all_agents}
        
        # Build children dictionary manually to ensure all relationships are captured
        children_by_parent_id = {}
        for agent in all_agents:
            if agent.parent_agent_id is not None:
                if agent.parent_agent_id not in children_by_parent_id:
                    children_by_parent_id[agent.parent_agent_id] = []
                children_by_parent_id[agent.parent_agent_id].append(agent)
        
        # Build hierarchical structure
        def build_agent_node(agent: Agent):
            """Build a node for an agent with its mapping info and all children"""
            mapping = mapping_dict.get(agent.id)
            
            # Get LLM credentials info if mapping exists
            llm_cred_info = None
            if mapping and mapping.llm_credentials:
                llm_cred_info = {
                    "id": mapping.llm_credentials.id,
                    "provider": mapping.llm_credentials.provider,
                    "available_models": mapping.llm_credentials.available_models,
                    "is_active": mapping.llm_credentials.is_active
                }
            
            node = {
                "agent_id": agent.id,
                "agent_name": agent.name,
                "agent_display_name": agent.display_name,
                "agent_description": agent.description,
                "agent_type": agent.agent_type,
                "parent_agent_id": agent.parent_agent_id,
                "default_model": agent.default_model,
                "is_mapped": mapping is not None,
                "mapping_info": None if not mapping else {
                    "mapping_id": mapping.id,
                    "llm_credentials_id": mapping.llm_credentials_id,
                    "llm_credentials": llm_cred_info,
                    "preferred_model": mapping.preferred_model,
                    "selected_model": mapping.selected_model,
                    "custom_system_prompt": mapping.custom_system_prompt,
                    "is_active": mapping.is_active,
                    "priority": mapping.priority,
                    "created_at": to_ist(mapping.created_at) if mapping.created_at else None,
                    "updated_at": to_ist(mapping.updated_at) if mapping.updated_at else None
                },
                "children": []
            }
            
            # Recursively add children using our manually built children dictionary
            child_agents = children_by_parent_id.get(agent.id, [])
            for child_agent in child_agents:
                node["children"].append(build_agent_node(child_agent))
            
            return node
        
        # Get root agents (agents with no parent)
        all_root_agents = [agent for agent in all_agents if agent.parent_agent_id is None]
        
        # Apply pagination to root agents
        total_root_count = len(all_root_agents)
        total_pages = (total_root_count + page_size - 1) // page_size if total_root_count > 0 else 1
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Get paginated root agents
        paginated_root_agents = all_root_agents[offset:offset + page_size]
        
        # Build hierarchy for paginated root agents (children are fully included)
        hierarchy = [build_agent_node(agent) for agent in paginated_root_agents]
        
        # Debug: Log hierarchy structure
        for root_node in hierarchy:
            def count_total_descendants(node, depth=0):
                count = len(node['children'])
                for child in node['children']:
                    count += count_total_descendants(child, depth + 1)
                return count
        
        # Get all LLM credentials for this company
        llm_credentials = db.query(LLMCredentials).filter(
            LLMCredentials.company_id == company_id,
            LLMCredentials.is_active == True
        ).all()
        
        llm_creds_list = [
            {
                "id": cred.id,
                "provider": cred.provider,
                "base_url": cred.base_url,
                "available_models": cred.available_models,
                "is_default": cred.is_default,
                "max_tokens": cred.max_tokens,
                "temperature": cred.temperature,
                "is_active": cred.is_active
            }
            for cred in llm_credentials
        ]
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Retrieved agent hierarchy for company {company.name} (page {page} of {total_pages})",
                "data": {
                    "company_id": company_id,
                    "company_name": company.name,
                    "agent_hierarchy": hierarchy,
                    "available_llm_credentials": llm_creds_list,
                    "total_agents": len(all_agents)
                },
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_items": total_root_count,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }
        )
    
    except Exception as e:
        logger.error(f"Error getting company agent mappings hierarchy: {str(e)}")
        raise


def get_agent_mappings_data(
    db: Session,
    company_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    is_active: Optional[bool] = None
):
    """
    Get agent mappings with optional filters.
    
    Args:
        db: Database session
        company_id: Filter by company ID
        agent_id: Filter by agent ID
        is_active: Filter by active status
    
    Returns:
        JSONResponse with agent mappings data
    """
    try:
        query = db.query(AgentMapping)
        
        # Apply filters
        if company_id:
            query = query.filter(AgentMapping.company_id == company_id)
        
        if agent_id:
            query = query.filter(AgentMapping.agent_id == agent_id)
        
        if is_active is not None:
            query = query.filter(AgentMapping.is_active == is_active)
        
        mappings = query.order_by(AgentMapping.priority.asc(), AgentMapping.created_at.desc()).all()
        
        mappings_data = [
            {
                "id": mapping.id,
                "company_id": mapping.company_id,
                "company_name": mapping.company.name if mapping.company else None,
                "agent_id": mapping.agent_id,
                "agent_name": mapping.agent.name if mapping.agent else None,
                "agent_display_name": mapping.agent.display_name if mapping.agent else None,
                "agent_type": mapping.agent.agent_type if mapping.agent else None,
                "llm_credentials_id": mapping.llm_credentials_id,
                "llm_provider": mapping.llm_credentials.provider if mapping.llm_credentials else None,
                "preferred_model": mapping.preferred_model,
                "selected_model": mapping.selected_model,
                "custom_system_prompt": mapping.custom_system_prompt,
                "is_active": mapping.is_active,
                "priority": mapping.priority,
                "created_at": to_ist(mapping.created_at) if mapping.created_at else None,
                "updated_at": to_ist(mapping.updated_at) if mapping.updated_at else None
            }
            for mapping in mappings
        ]
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Retrieved {len(mappings_data)} agent mappings",
                "data": mappings_data,
                "total": len(mappings_data)
            }
        )
    
    except Exception as e:
        logger.error(f"Error getting agent mappings: {str(e)}")
        raise


def create_agent_mapping_data(db: Session, mapping_data: Dict[str, Any], created_by: int = None):
    """
    Create a new agent mapping.
    
    Args:
        db: Database session
        mapping_data: Agent mapping data dictionary
        created_by: User ID who is creating the agent mapping
    
    Returns:
        JSONResponse with created agent mapping data
    """
    try:
        # Verify company exists
        company = db.query(Company).filter(Company.id == mapping_data["company_id"]).first()
        if not company:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": f"Company with ID {mapping_data['company_id']} does not exist"
                }
            )
        
        # Verify agent exists
        agent = db.query(Agent).filter(Agent.id == mapping_data["agent_id"]).first()
        if not agent:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": f"Agent with ID {mapping_data['agent_id']} does not exist"
                }
            )
        
        # Verify LLM credentials exist and belong to the company
        llm_cred = db.query(LLMCredentials).filter(
            LLMCredentials.id == mapping_data["llm_credentials_id"],
            LLMCredentials.company_id == mapping_data["company_id"]
        ).first()
        if not llm_cred:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": f"LLM credentials with ID {mapping_data['llm_credentials_id']} does not exist or does not belong to this company"
                }
            )
        
        # Check if mapping already exists (unique constraint: company_id + agent_id)
        existing_mapping = db.query(AgentMapping).filter(
            AgentMapping.company_id == mapping_data["company_id"],
            AgentMapping.agent_id == mapping_data["agent_id"]
        ).first()
        if existing_mapping:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": f"Agent mapping already exists for this company-agent combination"
                }
            )
        
        # If creating mapping for a subagent, check if parent agent is mapped and active
        if agent.parent_agent_id is not None:
            # Find parent agent mapping for the same company
            parent_mapping = db.query(AgentMapping).filter(
                AgentMapping.company_id == mapping_data["company_id"],
                AgentMapping.agent_id == agent.parent_agent_id
            ).first()
            
            if not parent_mapping:
                parent_agent = db.query(Agent).filter(Agent.id == agent.parent_agent_id).first()
                parent_agent_name = parent_agent.display_name or parent_agent.name if parent_agent else "Unknown"
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": f"Cannot create mapping for subagent '{agent.display_name or agent.name}'. Parent agent '{parent_agent_name}' must be mapped to this company first."
                    }
                )
            
            if not parent_mapping.is_active:
                parent_agent = parent_mapping.agent
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": f"Cannot create mapping for subagent '{agent.display_name or agent.name}'. Parent agent '{parent_agent.display_name or parent_agent.name}' must be activated first."
                    }
                )
        
        # Create new agent mapping
        agent_mapping = AgentMapping(
            company_id=mapping_data["company_id"],
            agent_id=mapping_data["agent_id"],
            llm_credentials_id=mapping_data["llm_credentials_id"],
            preferred_model=mapping_data.get("preferred_model"),
            selected_model=mapping_data.get("selected_model"),
            custom_system_prompt=mapping_data.get("custom_system_prompt"),
            is_active=mapping_data.get("is_active", True),
            priority=mapping_data.get("priority", 1),
            created_by=created_by,
            updated_by=created_by
        )
        
        db.add(agent_mapping)
        db.commit()
        db.refresh(agent_mapping)
        
        # Invalidate relevant caches after creating the mapping
        cache_invalidation_service.invalidate_agent_mapping_caches(
            db, agent_mapping.agent_id, agent_mapping.company_id
        )
        
        # Format response data
        created_mapping = {
            "id": agent_mapping.id,
            "company_id": agent_mapping.company_id,
            "company_name": agent_mapping.company.name if agent_mapping.company else None,
            "agent_id": agent_mapping.agent_id,
            "agent_name": agent_mapping.agent.name if agent_mapping.agent else None,
            "agent_display_name": agent_mapping.agent.display_name if agent_mapping.agent else None,
            "llm_credentials_id": agent_mapping.llm_credentials_id,
            "llm_provider": agent_mapping.llm_credentials.provider if agent_mapping.llm_credentials else None,
            "preferred_model": agent_mapping.preferred_model,
            "selected_model": agent_mapping.selected_model,
            "custom_system_prompt": agent_mapping.custom_system_prompt,
            "is_active": agent_mapping.is_active,
            "priority": agent_mapping.priority,
            "created_at": to_ist(agent_mapping.created_at) if agent_mapping.created_at else None,
            "updated_at": to_ist(agent_mapping.updated_at) if agent_mapping.updated_at else None,
            "created_by": agent_mapping.created_by,
            "updated_by": agent_mapping.updated_by
        }
        
        return JSONResponse(
            status_code=201,
            content={
                "status": "success",
                "message": "Agent mapping created successfully",
                "data": created_mapping
            }
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating agent mapping: {str(e)}")
        raise


def update_agent_mapping_data(db: Session, mapping_id: int, update_data: Dict[str, Any], updated_by: int = None):
    """
    Update an agent mapping by ID.
    
    Args:
        db: Database session
        mapping_id: Agent mapping ID
        update_data: Data to update
        updated_by: User ID who is updating the agent mapping
    
    Returns:
        JSONResponse with updated agent mapping data
    """
    try:
        # Find the agent mapping
        agent_mapping = db.query(AgentMapping).filter(AgentMapping.id == mapping_id).first()
        if not agent_mapping:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "Agent mapping not found"
                }
            )
        
        # Verify company if being updated
        if "company_id" in update_data:
            company = db.query(Company).filter(Company.id == update_data["company_id"]).first()
            if not company:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": f"Company with ID {update_data['company_id']} does not exist"
                    }
                )
        
        # Verify agent if being updated
        if "agent_id" in update_data:
            agent = db.query(Agent).filter(Agent.id == update_data["agent_id"]).first()
            if not agent:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": f"Agent with ID {update_data['agent_id']} does not exist"
                    }
                )
        
        # Verify LLM credentials if being updated
        if "llm_credentials_id" in update_data:
            company_id = update_data.get("company_id", agent_mapping.company_id)
            llm_cred = db.query(LLMCredentials).filter(
                LLMCredentials.id == update_data["llm_credentials_id"],
                LLMCredentials.company_id == company_id
            ).first()
            if not llm_cred:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": f"LLM credentials with ID {update_data['llm_credentials_id']} does not exist or does not belong to this company"
                    }
                )
        
        # Check for unique constraint violation if company_id or agent_id is being updated
        if "company_id" in update_data or "agent_id" in update_data:
            new_company_id = update_data.get("company_id", agent_mapping.company_id)
            new_agent_id = update_data.get("agent_id", agent_mapping.agent_id)
            
            existing_mapping = db.query(AgentMapping).filter(
                AgentMapping.company_id == new_company_id,
                AgentMapping.agent_id == new_agent_id,
                AgentMapping.id != mapping_id
            ).first()
            if existing_mapping:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": "Agent mapping already exists for this company-agent combination"
                    }
                )
        
        # Update fields
        for key, value in update_data.items():
            if hasattr(agent_mapping, key):
                setattr(agent_mapping, key, value)
        
        agent_mapping.updated_at = datetime.utcnow()
        if updated_by is not None:
            agent_mapping.updated_by = updated_by
        db.commit()
        db.refresh(agent_mapping)
        
        # Invalidate relevant caches after updating the mapping
        cache_invalidation_service.invalidate_agent_mapping_caches(
            db, agent_mapping.agent_id, agent_mapping.company_id
        )
        
        # Format response data
        updated_mapping = {
            "id": agent_mapping.id,
            "company_id": agent_mapping.company_id,
            "company_name": agent_mapping.company.name if agent_mapping.company else None,
            "agent_id": agent_mapping.agent_id,
            "agent_name": agent_mapping.agent.name if agent_mapping.agent else None,
            "agent_display_name": agent_mapping.agent.display_name if agent_mapping.agent else None,
            "llm_credentials_id": agent_mapping.llm_credentials_id,
            "llm_provider": agent_mapping.llm_credentials.provider if agent_mapping.llm_credentials else None,
            "preferred_model": agent_mapping.preferred_model,
            "selected_model": agent_mapping.selected_model,
            "custom_system_prompt": agent_mapping.custom_system_prompt,
            "is_active": agent_mapping.is_active,
            "priority": agent_mapping.priority,
            "created_at": to_ist(agent_mapping.created_at) if agent_mapping.created_at else None,
            "updated_at": to_ist(agent_mapping.updated_at) if agent_mapping.updated_at else None,
            "created_by": agent_mapping.created_by,
            "updated_by": agent_mapping.updated_by
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Agent mapping updated successfully",
                "data": updated_mapping
            }
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating agent mapping {mapping_id}: {str(e)}")
        raise


def delete_agent_mapping_data(db: Session, mapping_id: int):
    """
    Delete an agent mapping by ID.
    
    Args:
        db: Database session
        mapping_id: Agent mapping ID
    
    Returns:
        JSONResponse with deletion status
    """
    try:
        # Find the agent mapping
        agent_mapping = db.query(AgentMapping).filter(AgentMapping.id == mapping_id).first()
        if not agent_mapping:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "Agent mapping not found"
                }
            )
        
        # Store IDs before deletion for cache invalidation
        agent_id = agent_mapping.agent_id
        company_id = agent_mapping.company_id
        
        # Delete the mapping
        db.delete(agent_mapping)
        db.commit()
        
        # Invalidate relevant caches after deleting the mapping
        cache_invalidation_service.invalidate_agent_mapping_caches(
            db, agent_id, company_id
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Agent mapping deleted successfully"
            }
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting agent mapping {mapping_id}: {str(e)}")
        raise


def toggle_agent_mapping_status_data(db: Session, mapping_id: int, recursive: bool = False, updated_by: int = None):
    """
    Toggle the active status of an agent mapping.
    If deactivating a parent agent, all child agents are also deactivated (recursive).
    If activating a parent agent, child agents remain unchanged (manual control).
    
    Args:
        db: Database session
        mapping_id: Agent mapping ID
        recursive: If True, affects child agents (used for deactivation)
        updated_by: User ID who is toggling the agent mapping status
    
    Returns:
        JSONResponse with updated agent mapping data
    """
    try:
        # Find the agent mapping
        agent_mapping = db.query(AgentMapping).filter(AgentMapping.id == mapping_id).first()
        if not agent_mapping:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "Agent mapping not found"
                }
            )
        
        # Get the agent to check for children
        agent = agent_mapping.agent
        
        # Toggle the status
        new_status = not agent_mapping.is_active
        
        # If activating a subagent, check if parent agent is active
        if new_status and agent.parent_agent_id is not None:
            # Find parent agent mapping for the same company
            parent_mapping = db.query(AgentMapping).filter(
                AgentMapping.company_id == agent_mapping.company_id,
                AgentMapping.agent_id == agent.parent_agent_id
            ).first()
            
            if not parent_mapping:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": f"Cannot activate subagent '{agent.display_name or agent.name}'. Parent agent is not mapped to this company."
                    }
                )
            
            if not parent_mapping.is_active:
                parent_agent = parent_mapping.agent
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": f"Cannot activate subagent '{agent.display_name or agent.name}'. Parent agent '{parent_agent.display_name or parent_agent.name}' must be activated first."
                    }
                )
        
        agent_mapping.is_active = new_status
        agent_mapping.updated_at = datetime.utcnow()
        if updated_by is not None:
            agent_mapping.updated_by = updated_by
        
        affected_mappings = [agent_mapping.id]
        
        # If deactivating, build children lookup and deactivate all child agent mappings recursively
        if not new_status:
            # Get all agents to build children relationship
            all_agents = db.query(Agent).all()
            children_by_parent_id = {}
            for ag in all_agents:
                if ag.parent_agent_id is not None:
                    if ag.parent_agent_id not in children_by_parent_id:
                        children_by_parent_id[ag.parent_agent_id] = []
                    children_by_parent_id[ag.parent_agent_id].append(ag)
            
            def deactivate_children_recursive(parent_agent_id, company_id):
                """Recursively deactivate all child agent mappings"""
                child_agents = children_by_parent_id.get(parent_agent_id, [])
                for child_agent in child_agents:
                    # Find child agent's mapping for this company
                    child_mapping = db.query(AgentMapping).filter(
                        AgentMapping.company_id == company_id,
                        AgentMapping.agent_id == child_agent.id
                    ).first()
                    
                    if child_mapping and child_mapping.is_active:
                        child_mapping.is_active = False
                        child_mapping.updated_at = datetime.utcnow()
                        if updated_by is not None:
                            child_mapping.updated_by = updated_by
                        affected_mappings.append(child_mapping.id)
                        logger.info(f"Deactivated child agent mapping: {child_agent.name} (ID: {child_mapping.id})")
                        
                        # Recursively deactivate grandchildren
                        deactivate_children_recursive(child_agent.id, company_id)
            
            # Start recursive deactivation from current agent
            deactivate_children_recursive(agent.id, agent_mapping.company_id)
            logger.info(f"Deactivated agent '{agent.name}' and {len(affected_mappings) - 1} child agents for company {agent_mapping.company_id}")
        
        db.commit()
        db.refresh(agent_mapping)
        
        # Invalidate relevant caches after toggling status
        cache_invalidation_service.invalidate_agent_mapping_caches(
            db, agent_mapping.agent_id, agent_mapping.company_id
        )
        
        # Format response data
        updated_mapping = {
            "id": agent_mapping.id,
            "company_id": agent_mapping.company_id,
            "company_name": agent_mapping.company.name if agent_mapping.company else None,
            "agent_id": agent_mapping.agent_id,
            "agent_name": agent_mapping.agent.name if agent_mapping.agent else None,
            "agent_display_name": agent_mapping.agent.display_name if agent_mapping.agent else None,
            "llm_credentials_id": agent_mapping.llm_credentials_id,
            "llm_provider": agent_mapping.llm_credentials.provider if agent_mapping.llm_credentials else None,
            "preferred_model": agent_mapping.preferred_model,
            "selected_model": agent_mapping.selected_model,
            "custom_system_prompt": agent_mapping.custom_system_prompt,
            "is_active": agent_mapping.is_active,
            "priority": agent_mapping.priority,
            "created_at": to_ist(agent_mapping.created_at) if agent_mapping.created_at else None,
            "updated_at": to_ist(agent_mapping.updated_at) if agent_mapping.updated_at else None,
            "created_by": agent_mapping.created_by,
            "updated_by": agent_mapping.updated_by
        }
        
        status_text = "activated" if agent_mapping.is_active else "deactivated"
        message = f"Agent mapping {status_text} successfully"
        if len(affected_mappings) > 1:
            message += f" (affected {len(affected_mappings)} mappings including children)"
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": message,
                "data": updated_mapping,
                "affected_mapping_ids": affected_mappings
            }
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error toggling agent mapping status {mapping_id}: {str(e)}")
        raise


def get_agent_mapping_by_id_data(db: Session, mapping_id: int):
    """
    Get a single agent mapping by ID.
    
    Args:
        db: Database session
        mapping_id: Agent mapping ID
    
    Returns:
        JSONResponse with agent mapping data
    """
    try:
        agent_mapping = db.query(AgentMapping).filter(AgentMapping.id == mapping_id).first()
        if not agent_mapping:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "Agent mapping not found"
                }
            )
        
        # Get detailed agent info including children
        agent = agent_mapping.agent
        child_agents = []
        if agent and agent.children:
            for child in agent.children:
                # Check if child has mapping for this company
                child_mapping = db.query(AgentMapping).filter(
                    AgentMapping.company_id == agent_mapping.company_id,
                    AgentMapping.agent_id == child.id
                ).first()
                
                child_agents.append({
                    "id": child.id,
                    "name": child.name,
                    "display_name": child.display_name,
                    "agent_type": child.agent_type,
                    "is_mapped": child_mapping is not None,
                    "is_active": child_mapping.is_active if child_mapping else False
                })
        
        # Get LLM credentials details
        llm_cred = agent_mapping.llm_credentials
        llm_cred_details = None
        if llm_cred:
            llm_cred_details = {
                "id": llm_cred.id,
                "provider": llm_cred.provider,
                "base_url": llm_cred.base_url,
                "available_models": llm_cred.available_models,
                "is_default": llm_cred.is_default,
                "max_tokens": llm_cred.max_tokens,
                "temperature": llm_cred.temperature,
                "is_active": llm_cred.is_active
            }
        
        mapping_data = {
            "id": agent_mapping.id,
            "company_id": agent_mapping.company_id,
            "company_name": agent_mapping.company.name if agent_mapping.company else None,
            "agent_id": agent_mapping.agent_id,
            "agent_name": agent_mapping.agent.name if agent_mapping.agent else None,
            "agent_display_name": agent_mapping.agent.display_name if agent_mapping.agent else None,
            "agent_description": agent_mapping.agent.description if agent_mapping.agent else None,
            "agent_type": agent_mapping.agent.agent_type if agent_mapping.agent else None,
            "parent_agent_id": agent_mapping.agent.parent_agent_id if agent_mapping.agent else None,
            "llm_credentials_id": agent_mapping.llm_credentials_id,
            "llm_credentials": llm_cred_details,
            "preferred_model": agent_mapping.preferred_model,
            "selected_model": agent_mapping.selected_model,
            "custom_system_prompt": agent_mapping.custom_system_prompt,
            "is_active": agent_mapping.is_active,
            "priority": agent_mapping.priority,
            "created_at": to_ist(agent_mapping.created_at) if agent_mapping.created_at else None,
            "updated_at": to_ist(agent_mapping.updated_at) if agent_mapping.updated_at else None,
            "created_by": agent_mapping.created_by,
            "updated_by": agent_mapping.updated_by,
            "child_agents": child_agents
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Agent mapping retrieved successfully",
                "data": mapping_data
            }
        )
    
    except Exception as e:
        logger.error(f"Error getting agent mapping {mapping_id}: {str(e)}")
        raise

