"""
Network Activity Service

This service handles fetching network activity logs with filtering and pagination.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from database.models import NetworkActivityLog
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def get_network_activity_logs(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    endpoint: str = None,
    method: str = None,
    ip_address: str = None,
    device_type: str = None,
    user_id: str = None,
    company_id: str = None,
    date_from: str = None,
    date_to: str = None,
):
    """
    Fetch network activity logs with optional filters and pagination.
    
    Args:
        db: Database session
        page: Page number (starts from 1)
        page_size: Number of items per page
        endpoint: Filter by endpoint
        method: Filter by HTTP method
        ip_address: Filter by IP address
        device_type: Filter by device type (mobile, desktop, tablet, bot)
        user_id: Filter by user ID
        company_id: Filter by company ID
        date_from: Start date filter (YYYY-MM-DD format)
        date_to: End date filter (YYYY-MM-DD format)
        
    Returns:
        dict: Paginated network activity logs with metadata
    """
    try:
        # Build the query with filters
        query = db.query(NetworkActivityLog)
        
        # Apply filters
        filters = []
        
        if endpoint:
            filters.append(NetworkActivityLog.endpoint.ilike(f"%{endpoint}%"))
        
        if method:
            filters.append(NetworkActivityLog.method == method.upper())
        
        if ip_address:
            filters.append(NetworkActivityLog.ip_address.ilike(f"%{ip_address}%"))
        
        if device_type:
            filters.append(NetworkActivityLog.device_type == device_type)
        
        if user_id:
            filters.append(NetworkActivityLog.user_id.ilike(f"%{user_id}%"))
        
        if company_id:
            filters.append(NetworkActivityLog.company_id == company_id)
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
                filters.append(NetworkActivityLog.created_at >= date_from_obj)
            except ValueError:
                logger.warning(f"Invalid date_from format: {date_from}")
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
                # Add one day to include the entire end date
                from datetime import timedelta
                date_to_obj = date_to_obj + timedelta(days=1)
                filters.append(NetworkActivityLog.created_at < date_to_obj)
            except ValueError:
                logger.warning(f"Invalid date_to format: {date_to}")
        
        # Apply all filters
        if filters:
            query = query.filter(and_(*filters))
        
        # Get total count before pagination
        total_count = query.count()
        
        # Calculate pagination
        offset = (page - 1) * page_size
        total_pages = (total_count + page_size - 1) // page_size
        
        # Get paginated results ordered by created_at descending (newest first)
        logs = query.order_by(desc(NetworkActivityLog.created_at)).offset(offset).limit(page_size).all()
        
        # Convert to dict
        logs_data = []
        for log in logs:
            logs_data.append({
                "id": log.id,
                "endpoint": log.endpoint,
                "method": log.method,
                "ip_address": log.ip_address,
                "forwarded_for": log.forwarded_for,
                "user_agent": log.user_agent,
                "device_type": log.device_type,
                "browser": log.browser,
                "browser_version": log.browser_version,
                "os": log.os,
                "os_version": log.os_version,
                "platform": log.platform,
                "user_id": log.user_id,
                "session_id": log.session_id,
                "company_id": log.company_id,
                "origin": log.origin,
                "referer": log.referer,
                "host": log.host,
                "status_code": log.status_code,
                "request_id": log.request_id,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            })
        
        return {
            "status": "success",
            "data": logs_data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching network activity logs: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to fetch network activity logs: {str(e)}",
            "data": [],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": 0,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False,
            }
        }


def get_network_activity_stats(db: Session):
    """
    Get statistics about network activity logs.
    
    Args:
        db: Database session
        
    Returns:
        dict: Statistics about network activity
    """
    try:
        # Total requests
        total_requests = db.query(func.count(NetworkActivityLog.id)).scalar()
        
        # Requests by device type
        device_stats = db.query(
            NetworkActivityLog.device_type,
            func.count(NetworkActivityLog.id).label('count')
        ).group_by(NetworkActivityLog.device_type).all()
        
        # Top endpoints
        endpoint_stats = db.query(
            NetworkActivityLog.endpoint,
            func.count(NetworkActivityLog.id).label('count')
        ).group_by(NetworkActivityLog.endpoint).order_by(desc('count')).limit(10).all()
        
        # Top IP addresses
        ip_stats = db.query(
            NetworkActivityLog.ip_address,
            func.count(NetworkActivityLog.id).label('count')
        ).filter(NetworkActivityLog.ip_address.isnot(None)).group_by(
            NetworkActivityLog.ip_address
        ).order_by(desc('count')).limit(10).all()
        
        # Browser distribution
        browser_stats = db.query(
            NetworkActivityLog.browser,
            func.count(NetworkActivityLog.id).label('count')
        ).filter(NetworkActivityLog.browser.isnot(None)).group_by(
            NetworkActivityLog.browser
        ).order_by(desc('count')).all()
        
        return {
            "status": "success",
            "data": {
                "total_requests": total_requests,
                "device_distribution": [{"device_type": d[0], "count": d[1]} for d in device_stats],
                "top_endpoints": [{"endpoint": e[0], "count": e[1]} for e in endpoint_stats],
                "top_ips": [{"ip_address": i[0], "count": i[1]} for i in ip_stats],
                "browser_distribution": [{"browser": b[0], "count": b[1]} for b in browser_stats],
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching network activity stats: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to fetch network activity stats: {str(e)}",
            "data": {}
        }

