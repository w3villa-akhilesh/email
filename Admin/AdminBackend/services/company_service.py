from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from fastapi.responses import JSONResponse
from fastapi import HTTPException
from datetime import datetime

from database.models import Company, AgentMapping, LLMCredentials
from services.timezone_utils import to_ist
from services.cache_invalidation_service import cache_invalidation_service
from logger import logger


def get_companies_data(
    db: Session, 
    name: Optional[str] = None,
    origin: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 10
):
    """
    Get companies with optional filters and pagination.
    
    Args:
        db: Database session
        name: Filter by company name (partial match, case-insensitive)
        origin: Filter by origin (partial match, case-insensitive)
        is_active: Filter by active status (True/False/None for all)
        page: Page number (starts from 1)
        page_size: Number of items per page
    
    Returns:
        JSONResponse with paginated companies data
    """
    try:
        query = db.query(Company)
        
        # Apply filters if provided
        if name:
            query = query.filter(Company.name.ilike(f"%{name}%"))
        
        if origin:
            query = query.filter(Company.origin.ilike(f"%{origin}%"))
        
        if is_active is not None:
            query = query.filter(Company.is_active == is_active)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        companies = query.order_by(Company.created_at.desc()).offset(offset).limit(page_size).all()
        
        # Calculate pagination metadata
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1
        
        companies_data = []
        for company in companies:
            # Count active agent mappings for this company
            active_agent_mappings_count = db.query(AgentMapping).filter(
                AgentMapping.company_id == company.id,
                AgentMapping.is_active == True
            ).count()
            
            companies_data.append({
                "id": company.id,
                "name": company.name,
                "origin": company.origin,
                "description": company.description,
                "company_id": company.company_id,
                "created_at": to_ist(company.created_at) if company.created_at else None,
                "updated_at": to_ist(company.updated_at) if company.updated_at else None,
                "created_by": company.created_by,
                "updated_by": company.updated_by,
                "is_active": company.is_active,
                "active_agent_mappings_count": active_agent_mappings_count
            })
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Retrieved {len(companies_data)} companies (page {page} of {total_pages})",
                "data": companies_data,
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
        logger.error(f"Error getting companies data: {str(e)}")
        raise


def get_company_by_id_data(db: Session, company_id: int):
    """
    Get a single company by ID.
    
    Args:
        db: Database session
        company_id: Company ID
    
    Returns:
        JSONResponse with company data
    """
    try:
        # Find the company
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "Company not found"
                }
            )
        
        # Count active agent mappings for this company
        active_agent_mappings_count = db.query(AgentMapping).filter(
            AgentMapping.company_id == company.id,
            AgentMapping.is_active == True
        ).count()
        
        # Format response data
        company_data = {
            "id": company.id,
            "name": company.name,
            "origin": company.origin,
            "description": company.description,
            "company_id": company.company_id,
            "created_at": to_ist(company.created_at) if company.created_at else None,
            "updated_at": to_ist(company.updated_at) if company.updated_at else None,
            "created_by": company.created_by,
            "updated_by": company.updated_by,
            "is_active": company.is_active,
            "active_agent_mappings_count": active_agent_mappings_count
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Company retrieved successfully",
                "data": company_data
            }
        )
    
    except Exception as e:
        logger.error(f"Error getting company {company_id}: {str(e)}")
        raise


def create_company_data(db: Session, company_data: Dict[str, Any], created_by: int = None):
    """
    Create a new company.
    
    Args:
        db: Database session
        company_data: Company data dictionary (must include 'id')
        created_by: User ID who is creating the company
    
    Returns:
        JSONResponse with created company data
    """
    try:
        # Validate that ID is provided
        if "id" not in company_data or company_data["id"] is None:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "Company ID is required"
                }
            )
        
        # Check if company with same ID already exists
        existing_company_by_id = db.query(Company).filter(Company.id == company_data["id"]).first()
        if existing_company_by_id:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": f"Company with ID '{company_data['id']}' already exists"
                }
            )
        
        # Check if company with same origin already exists
        existing_company_by_origin = db.query(Company).filter(Company.origin == company_data["origin"]).first()
        if existing_company_by_origin:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": f"Company with origin '{company_data['origin']}' already exists"
                }
            )
        
        # Create new company
        company = Company(
            id=company_data["id"],
            name=company_data["name"],
            origin=company_data["origin"],
            description=company_data.get("description"),
            company_id=company_data.get("company_id"),
            is_active=company_data.get("is_active", True),
            created_by=created_by,
            updated_by=created_by
        )
        
        db.add(company)
        db.commit()
        db.refresh(company)
        
        # Count active agent mappings (will be 0 for new company)
        active_agent_mappings_count = 0
        
        # Format response data
        created_company = {
            "id": company.id,
            "name": company.name,
            "origin": company.origin,
            "description": company.description,
            "company_id": company.company_id,
            "created_at": to_ist(company.created_at) if company.created_at else None,
            "updated_at": to_ist(company.updated_at) if company.updated_at else None,
            "created_by": company.created_by,
            "updated_by": company.updated_by,
            "is_active": company.is_active,
            "active_agent_mappings_count": active_agent_mappings_count
        }
        
        return JSONResponse(
            status_code=201,
            content={
                "status": "success",
                "message": "Company created successfully",
                "data": created_company
            }
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating company: {str(e)}")
        raise


def update_company_data(db: Session, company_id: int, update_data: Dict[str, Any], updated_by: int = None):
    """
    Update a company by ID.
    
    Args:
        db: Database session
        company_id: Company ID
        update_data: Data to update
        updated_by: User ID who is updating the company
    
    Returns:
        JSONResponse with updated company data
    """
    try:
        # Find the company
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "Company not found"
                }
            )
        
        # Check if origin is being updated and if it conflicts with existing company
        if "origin" in update_data and update_data["origin"] != company.origin:
            existing_company = db.query(Company).filter(
                Company.origin == update_data["origin"],
                Company.id != company_id
            ).first()
            if existing_company:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": f"Company with origin '{update_data['origin']}' already exists"
                    }
                )
        
        # Update fields
        for key, value in update_data.items():
            if hasattr(company, key):
                setattr(company, key, value)
        
        company.updated_at = datetime.utcnow()
        if updated_by is not None:
            company.updated_by = updated_by
        db.commit()
        db.refresh(company)
        
        # Invalidate all caches related to this company
        cache_invalidation_service.invalidate_all_company_caches(db, company_id)
        
        # Count active agent mappings for this company
        active_agent_mappings_count = db.query(AgentMapping).filter(
            AgentMapping.company_id == company.id,
            AgentMapping.is_active == True
        ).count()
        
        # Format response data
        updated_company = {
            "id": company.id,
            "name": company.name,
            "origin": company.origin,
            "description": company.description,
            "company_id": company.company_id,
            "created_at": to_ist(company.created_at) if company.created_at else None,
            "updated_at": to_ist(company.updated_at) if company.updated_at else None,
            "created_by": company.created_by,
            "updated_by": company.updated_by,
            "is_active": company.is_active,
            "active_agent_mappings_count": active_agent_mappings_count
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Company updated successfully",
                "data": updated_company
            }
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating company {company_id}: {str(e)}")
        raise


def delete_company_data(db: Session, company_id: int):
    """
    Delete a company by ID with relationship integrity checks.
    
    Args:
        db: Database session
        company_id: Company ID
    
    Returns:
        JSONResponse with deletion status
    """
    try:
        # Find the company
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "Company not found"
                }
            )
        
        # Check for dependent records
        agent_mappings_count = db.query(AgentMapping).filter(AgentMapping.company_id == company_id).count()
        llm_credentials_count = db.query(LLMCredentials).filter(LLMCredentials.company_id == company_id).count()
        
        if agent_mappings_count > 0 or llm_credentials_count > 0:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": f"Cannot delete company. It has {agent_mappings_count} agent mappings and {llm_credentials_count} LLM credentials associated with it. Please remove these dependencies first."
                }
            )
        
        # Safe to delete - no dependencies
        db.delete(company)
        db.commit()
        
        # Invalidate all caches related to this company
        cache_invalidation_service.invalidate_all_company_caches(db, company_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Company deleted successfully"
            }
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting company {company_id}: {str(e)}")
        raise


def toggle_company_status_data(db: Session, company_id: int, updated_by: int = None):
    """
    Toggle the active status of a company.
    
    Args:
        db: Database session
        company_id: Company ID
        updated_by: User ID who is toggling the company status
    
    Returns:
        JSONResponse with updated company data
    """
    try:
        # Find the company
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "Company not found"
                }
            )
        
        # Toggle the status
        company.is_active = not company.is_active
        company.updated_at = datetime.utcnow()
        if updated_by is not None:
            company.updated_by = updated_by
        db.commit()
        db.refresh(company)
        
        # Invalidate all caches related to this company
        cache_invalidation_service.invalidate_all_company_caches(db, company_id)
        
        # Count active agent mappings for this company
        active_agent_mappings_count = db.query(AgentMapping).filter(
            AgentMapping.company_id == company.id,
            AgentMapping.is_active == True
        ).count()
        
        # Format response data
        updated_company = {
            "id": company.id,
            "name": company.name,
            "origin": company.origin,
            "description": company.description,
            "company_id": company.company_id,
            "created_at": to_ist(company.created_at) if company.created_at else None,
            "updated_at": to_ist(company.updated_at) if company.updated_at else None,
            "created_by": company.created_by,
            "updated_by": company.updated_by,
            "is_active": company.is_active,
            "active_agent_mappings_count": active_agent_mappings_count
        }
        
        status_text = "activated" if company.is_active else "deactivated"
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Company {status_text} successfully",
                "data": updated_company
            }
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error toggling company status {company_id}: {str(e)}")
        raise