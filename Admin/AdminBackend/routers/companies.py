from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional

from database.connection import get_db
from services.company_service import get_companies_data, get_company_by_id_data, create_company_data, update_company_data, delete_company_data, toggle_company_status_data
from services.user_context_service import get_current_user
from schemas import CompanyCreate, CompanyUpdate
from routers.auth import validate_token, get_token
from logger import logger

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("")
def companies_data(
    name: Optional[str] = Query(None, description="Search by company name (partial match, case-insensitive)"),
    origin: Optional[str] = Query(None, description="Search by origin (partial match, case-insensitive)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status (true/false, omit for all)"),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page (1-100)"),
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    """
    Get all companies with optional search filters and pagination.
    
    Search Parameters:
    - name: Search companies by name (partial match, case-insensitive)
    - origin: Search companies by origin (partial match, case-insensitive)  
    - is_active: Filter by active status (true for active, false for inactive, omit for all)
    - page: Page number (starts from 1)
    - page_size: Number of items per page (1-100)
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        return get_companies_data(db, name=name, origin=origin, is_active=is_active, page=page, page_size=page_size)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in companies_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{company_id}")
def get_company_by_id(
    company_id: int,
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    """
    Get a single company by ID.
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        return get_company_by_id_data(db, company_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_company_by_id: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("")
def create_company(
    company: CompanyCreate,
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db),
    current_user_id: Optional[int] = Depends(get_current_user)
):
    """
    Create a new company.
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        return create_company_data(db, company.dict(), created_by=current_user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_company: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.put("/{company_id}")
def update_company(
    company_id: int,
    company_update: CompanyUpdate,
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db),
    current_user_id: Optional[int] = Depends(get_current_user)
):
    """
    Update a company by ID.
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        # Only include fields that were actually provided
        update_data = company_update.dict(exclude_unset=True)
        return update_company_data(db, company_id, update_data, updated_by=current_user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_company: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/{company_id}")
def delete_company(
    company_id: int,
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    """
    Delete a company by ID.
    
    This will check for dependent records (AgentMappings and LLMCredentials) 
    and prevent deletion if dependencies exist to maintain referential integrity.
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        return delete_company_data(db, company_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_company: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.put("/{company_id}/toggle-status")
def toggle_company_status(
    company_id: int,
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db),
    current_user_id: Optional[int] = Depends(get_current_user)
):
    """
    Toggle the active status of a company (active <-> inactive).
    
    This endpoint switches the is_active field between True and False.
    
    Requires a valid access token for authentication.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        return toggle_company_status_data(db, company_id, updated_by=current_user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in toggle_company_status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")