from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional

from database.connection import get_db
from services.agent_mapping_service import (
    get_agent_mappings_data,
    get_company_agent_mappings_hierarchy,
    create_agent_mapping_data,
    update_agent_mapping_data,
    delete_agent_mapping_data,
    toggle_agent_mapping_status_data,
    get_agent_mapping_by_id_data
)
from services.user_context_service import get_current_user
from schemas import AgentMappingCreate, AgentMappingUpdate
from routers.auth import validate_token, get_token
from logger import logger

router = APIRouter(prefix="/agent-mappings", tags=["agent-mappings"])


@router.get("/company/{company_id}/hierarchy")
def get_company_agents_hierarchy(
    company_id: int,
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of root agents per page (1-100)"),
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    """
    Get agents for a company organized in a hierarchical tree structure with pagination.
    
    This endpoint returns:
    - Paginated agent hierarchy (parent-child relationships)
    - Mapping status for each agent (whether it's mapped to the company or not)
    - LLM credentials configuration for mapped agents
    - All available LLM credentials for the company
    
    Pagination is applied at the root agent level (agents with no parent).
    All children of paginated root agents are included in the response.
    
    Query Parameters:
    - page: Page number (starts from 1, default: 1)
    - page_size: Number of root agents per page (1-100, default: 10)
    
    Perfect for displaying agents in an expandable/collapsible tree view.
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        return get_company_agent_mappings_hierarchy(db, company_id, page, page_size)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_company_agents_hierarchy: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("")
def agent_mappings_data(
    company_id: Optional[int] = Query(None, description="Filter by company ID"),
    agent_id: Optional[int] = Query(None, description="Filter by agent ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status (true/false, omit for all)"),
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    """
    Get all agent mappings with optional search filters.
    
    Search Parameters:
    - company_id: Filter mappings by company ID
    - agent_id: Filter mappings by agent ID
    - is_active: Filter by active status (true for active, false for inactive, omit for all)
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        return get_agent_mappings_data(db, company_id=company_id, agent_id=agent_id, is_active=is_active)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in agent_mappings_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{mapping_id}")
def get_agent_mapping_by_id(
    mapping_id: int,
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    """
    Get a single agent mapping by ID with detailed information.
    
    Returns detailed information including:
    - Agent details
    - Company details
    - LLM credentials configuration
    - Child agents (if parent agent)
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        return get_agent_mapping_by_id_data(db, mapping_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_agent_mapping_by_id: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("")
def create_agent_mapping(
    mapping: AgentMappingCreate,
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db),
    current_user_id: Optional[int] = Depends(get_current_user)
):
    """
    Create a new agent mapping (link an agent to a company with LLM credentials).
    
    Required fields:
    - company_id: ID of the company
    - agent_id: ID of the agent to map
    - llm_credentials_id: ID of the LLM credentials to use (must belong to the company)
    
    Optional fields:
    - preferred_model: Preferred LLM model for this agent-company combination
    - selected_model: Currently selected model for this mapping
    - custom_system_prompt: Company-specific custom system prompt
    - is_active: Active status (defaults to true)
    - priority: Priority for ordering (defaults to 1)
    
    Note: The combination of company_id and agent_id must be unique.
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        return create_agent_mapping_data(db, mapping.dict(), created_by=current_user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_agent_mapping: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.put("/{mapping_id}")
def update_agent_mapping(
    mapping_id: int,
    mapping_update: AgentMappingUpdate,
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db),
    current_user_id: Optional[int] = Depends(get_current_user)
):
    """
    Update an agent mapping by ID.
    
    All fields are optional - only provide the fields you want to update:
    - company_id: ID of the company
    - agent_id: ID of the agent
    - llm_credentials_id: ID of the LLM credentials (must belong to the company)
    - preferred_model: Preferred LLM model
    - selected_model: Currently selected model
    - custom_system_prompt: Custom system prompt
    - is_active: Active status
    - priority: Priority for ordering
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        # Only include fields that were actually provided
        update_data = mapping_update.dict(exclude_unset=True)
        return update_agent_mapping_data(db, mapping_id, update_data, updated_by=current_user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_agent_mapping: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/{mapping_id}")
def delete_agent_mapping(
    mapping_id: int,
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    """
    Delete an agent mapping by ID.
    
    This removes the link between the agent and the company.
    The agent itself is not deleted, only the mapping.
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        return delete_agent_mapping_data(db, mapping_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_agent_mapping: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.put("/{mapping_id}/toggle-status")
def toggle_agent_mapping_status(
    mapping_id: int,
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db),
    current_user_id: Optional[int] = Depends(get_current_user)
):
    """
    Toggle the active status of an agent mapping (active <-> inactive).
    
    Special behavior:
    - Deactivating a parent agent: Automatically deactivates ALL child agents recursively
    - Activating a parent agent: Child agents remain unchanged, allowing manual control
    
    This endpoint switches the is_active field between True and False.
    
    Returns:
    - Updated agent mapping data
    - List of affected mapping IDs (includes children if parent was deactivated)
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        return toggle_agent_mapping_status_data(db, mapping_id, updated_by=current_user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in toggle_agent_mapping_status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/bulk-create")
def bulk_create_agent_mappings(
    mappings: list[AgentMappingCreate],
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    """
    Create multiple agent mappings at once.
    
    Useful for:
    - Setting up a new company with multiple agents
    - Bulk enabling agents for a company
    
    Returns:
    - List of successfully created mappings
    - List of errors for failed mappings
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        
        results = {
            "success": [],
            "errors": []
        }
        
        for idx, mapping in enumerate(mappings):
            try:
                response = create_agent_mapping_data(db, mapping.dict())
                if response.status_code == 201:
                    import json
                    response_data = json.loads(response.body.decode('utf-8'))
                    results["success"].append(response_data["data"])
                else:
                    import json
                    response_data = json.loads(response.body.decode('utf-8'))
                    results["errors"].append({
                        "index": idx,
                        "mapping": mapping.dict(),
                        "error": response_data.get("message", "Unknown error")
                    })
            except Exception as e:
                results["errors"].append({
                    "index": idx,
                    "mapping": mapping.dict(),
                    "error": str(e)
                })
        
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Processed {len(mappings)} mappings: {len(results['success'])} successful, {len(results['errors'])} failed",
                "data": results
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk_create_agent_mappings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

