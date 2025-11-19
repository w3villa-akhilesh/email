from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from database.connection import get_db
from services.dashboard import get_dashboard_data
from routers.auth import validate_token, get_token
from logger import logger

router = APIRouter(tags=["dashboard"])

@router.get("/dashboard_data")
def dashboard_data(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    access_token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    """
    Returns grouped session counts per app per date for the given date range.
    If start_date or end_date is not provided, defaults to the last 7 days including today.
    Requires a valid access token.
    """
    try:
        # Validate the access token
        validate_token(access_token)
        return get_dashboard_data(db, start_date=start_date, end_date=end_date)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in dashboard_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
