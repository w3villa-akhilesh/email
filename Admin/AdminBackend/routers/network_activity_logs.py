from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from database.connection import get_db
from routers.auth import get_token, validate_token
from services.network_activity_service import (
    get_network_activity_logs,
    get_network_activity_stats
)
from logger import logger

router = APIRouter(tags=["network-activity"])

@router.get("/network-activity-logs")
def get_network_activity_logs_endpoint(
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    endpoint: Optional[str] = Query(None, description="Filter by endpoint"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    ip_address: Optional[str] = Query(None, description="Filter by IP address"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    company_id: Optional[str] = Query(None, description="Filter by company ID"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
):
    """
    Get paginated network activity logs with optional filters.
    Requires a valid access token.
    """
    try:
        # Token validation
        validate_token(access_token)

        # Get the logs
        result = get_network_activity_logs(
            db=db,
            page=page,
            page_size=page_size,
            endpoint=endpoint,
            method=method,
            ip_address=ip_address,
            device_type=device_type,
            user_id=user_id,
            company_id=company_id,
            date_from=date_from,
            date_to=date_to,
        )
        
        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_network_activity_logs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/network-activity-stats")
def get_network_activity_stats_endpoint(
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    """
    Get statistics about network activity logs.
    Requires a valid access token.
    """
    try:
        # Token validation
        validate_token(access_token)

        # Get the stats
        result = get_network_activity_stats(db)
        
        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_network_activity_stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

