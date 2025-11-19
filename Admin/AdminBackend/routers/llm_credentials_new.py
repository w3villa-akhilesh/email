from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from database.connection import get_db
from services.llm_credential_service import (
    get_llm_credential_data,
    get_llm_credential_by_id_data,
    create_llm_credential_data,
    update_llm_credential_data,
    delete_llm_credential_data,
    toggle_llm_credential_status_data,
    toggle_llm_credential_crm_flow_data,
    get_llm_credentials_by_company_and_agent_data
)
from services.user_context_service import get_current_user
from schemas import LLMCredentialsNewCreate, LLMCredentialsNewUpdate
from routers.auth import validate_token, get_token
from config import config
from logger import logger

router = APIRouter(prefix="/llm-credential", tags=["llm-credential"])

# Separate router for plural endpoint (backward compatibility with existing API)
router_plural = APIRouter(prefix="/llm-credentials", tags=["llm-credentials"])

@router_plural.get("/find")
def find_llm_credentials_by_app(
    company_id: int = Query(..., description="Company ID"),
    app_name: str = Query(..., description="Application/Agent name"),
    origin: Optional[str] = Query(None, description="Origin URL"),
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    """
    Get LLM credentials by company_id and app_name (with optional origin).
    
    This is a separate endpoint to support the existing API format with app_name parameter.
    
    Query Parameters:
    - company_id: (required) Company ID
    - app_name: (required) Application/Agent name (e.g., resume_parser, interview_taker)
    - origin: (optional) Origin URL for additional context
    
    Requires authentication token in Authorization header (hardcoded token validation).
    
    Returns:
    - 200: Success with LLM credentials data
    - 401: Invalid authentication token
    - 404: Company, agent, or credentials not found
    - 400: Entity is inactive with specific details
    - 500: Internal server error
    """
    try:
        # Validate hardcoded token from environment
        if not config.AUTH_TOKEN:
            return JSONResponse(status_code=500, content={
                "success": False, 
                "error": "Authentication token not configured", 
                "data": None
            })
        
        if access_token != config.AUTH_TOKEN:
            return JSONResponse(status_code=401, content={
                "success": False, 
                "error": "Invalid authentication token", 
                "data": None
            })
        
        # Call service function to handle the business logic
        # Note: origin parameter is passed but currently not used in service logic
        return get_llm_credentials_by_company_and_agent_data(db, company_id, app_name, origin)

    except Exception as e:
        logger.error(f"Error in find_llm_credentials_by_app: {str(e)}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": f"Internal server error: {str(e)}",
            "data": None
        })


@router.get("/find-by-agent")
def get_llm_credentials_by_company_and_agent(
    company_id: int = Query(..., description="Company ID"),
    agent_name: str = Query(..., description="Agent name"),
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    """
    Get LLM credentials by company_id and agent_name.
    
    This endpoint:
    1. Verifies the company exists and is active
    2. Verifies the agent exists by name and is active
    3. Finds the agent mapping for the company and agent
    4. Retrieves the associated LLM credentials and verifies it's active
    5. Returns company details, agent details, and LLM credentials
    
    Requires authentication token in Authorization header (hardcoded token validation).
    
    Returns:
    - 200: Success with company, agent, and LLM credentials data
    - 401: Invalid authentication token
    - 404: Company, agent, or credentials not found
    - 400: Entity is inactive with specific details
    - 500: Internal server error
    """
    try:
        # Validate hardcoded token from environment
        if not config.AUTH_TOKEN:
            return JSONResponse(status_code=500, content={
                "success": False, 
                "error": "Authentication token not configured", 
                "data": None
            })
        
        if access_token != config.AUTH_TOKEN:
            return JSONResponse(status_code=401, content={
                "success": False, 
                "error": "Invalid authentication token", 
                "data": None
            })
        
        # Call service function to handle the business logic
        return get_llm_credentials_by_company_and_agent_data(db, company_id, agent_name)

    except Exception as e:
        logger.error(f"Error in get_llm_credentials_by_company_and_agent: {str(e)}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": f"Internal server error: {str(e)}",
            "data": None
        })


@router.get("")
def llm_credentials_data(
    company_id: Optional[int] = Query(None, description="Filter by company ID"),
    provider: Optional[str] = Query(None, description="Search by provider (partial match, case-insensitive)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status (true/false, omit for all)"),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page (1-100)"),
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    """
    Get all LLM credentials with optional search filters and pagination.
    
    Search Parameters:
    - company_id: Filter by company ID
    - provider: Search providers by name (partial match, case-insensitive)  
    - is_active: Filter by active status (true for active, false for inactive, omit for all)
    - page: Page number (starts from 1)
    - page_size: Number of items per page (1-100)
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        return get_llm_credential_data(db, company_id=company_id, provider=provider, is_active=is_active, page=page, page_size=page_size)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in llm_credentials_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{credentials_id}")
def get_llm_credential_by_id(
    credentials_id: int,
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    """
    Get a single LLM credential by ID.
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        return get_llm_credential_by_id_data(db, credentials_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_llm_credential_by_id: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("")
def create_llm_credentials(
    credentials: LLMCredentialsNewCreate,
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db),
    current_user_id: Optional[int] = Depends(get_current_user)
):
    """
    Create new LLM credentials.
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        return create_llm_credential_data(db, credentials.dict(), created_by=current_user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_llm_credentials: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.put("/{credentials_id}")
def update_llm_credentials(
    credentials_id: int,
    credentials_update: LLMCredentialsNewUpdate,
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db),
    current_user_id: Optional[int] = Depends(get_current_user)
):
    """
    Update LLM credentials by ID.
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        # Only include fields that were actually provided
        update_data = credentials_update.dict(exclude_unset=True)
        return update_llm_credential_data(db, credentials_id, update_data, updated_by=current_user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_llm_credentials: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/{credentials_id}")
def delete_llm_credentials(
    credentials_id: int,
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    """
    Delete LLM credentials by ID.
    
    This will check for dependent records (AgentMappings) 
    and prevent deletion if dependencies exist to maintain referential integrity.
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        return delete_llm_credential_data(db, credentials_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_llm_credentials: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.put("/{credentials_id}/toggle-status")
def toggle_llm_credentials_status(
    credentials_id: int,
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db),
    current_user_id: Optional[int] = Depends(get_current_user)
):
    """
    Toggle the active status of LLM credentials (active <-> inactive).
    
    This endpoint switches the is_active field between True and False.
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        return toggle_llm_credential_status_data(db, credentials_id, updated_by=current_user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in toggle_llm_credentials_status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.put("/{credentials_id}/toggle-crm-flow")
def toggle_llm_credentials_crm_flow(
    credentials_id: int,
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db),
    current_user_id: Optional[int] = Depends(get_current_user)
):
    """
    Toggle the CRM flow status of LLM credentials (enabled <-> disabled).
    
    This endpoint switches the is_crm_flow_active field between True and False.
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        return toggle_llm_credential_crm_flow_data(db, credentials_id, updated_by=current_user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in toggle_llm_credentials_crm_flow: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
