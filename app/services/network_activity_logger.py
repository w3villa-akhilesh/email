"""
Network Activity Logger Service

This service captures and stores network activity details for security monitoring.
It extracts IP addresses, device information, browser details, and other metadata
from incoming HTTP requests and stores them in the database.
"""

import uuid
import re
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import Request
from sqlalchemy.orm import Session
from app.models.db_models import NetworkActivityLog
from app.utils.logger import logger


class UserAgentParser:
    """
    Parses User-Agent strings to extract device, browser, and OS information.
    """
    
    # Browser patterns
    BROWSERS = {
        'Chrome': r'Chrome\/([\d\.]+)',
        'Firefox': r'Firefox\/([\d\.]+)',
        'Safari': r'Version\/([\d\.]+).*Safari',
        'Edge': r'Edg\/([\d\.]+)',
        'Opera': r'OPR\/([\d\.]+)',
        'IE': r'MSIE ([\d\.]+)',
        'Samsung': r'SamsungBrowser\/([\d\.]+)',
    }
    
    # OS patterns
    OPERATING_SYSTEMS = {
        'Windows': r'Windows NT ([\d\.]+)',
        'macOS': r'Mac OS X ([\d_\.]+)',
        'iOS': r'iPhone OS ([\d_]+)|iPad.*OS ([\d_]+)',
        'Android': r'Android ([\d\.]+)',
        'Linux': r'Linux',
        'Ubuntu': r'Ubuntu',
        'ChromeOS': r'CrOS',
    }
    
    # Device patterns
    DEVICE_PATTERNS = {
        'mobile': r'Mobile|iPhone|iPod|Android.*Mobile|BlackBerry|IEMobile',
        'tablet': r'iPad|Android(?!.*Mobile)|Tablet',
        'bot': r'bot|crawler|spider|scraper|curl|wget|python-requests|http|postman',
    }
    
    @staticmethod
    def parse(user_agent: str) -> Dict[str, Optional[str]]:
        """
        Parse user agent string and extract device, browser, and OS information.
        
        Args:
            user_agent: Raw user agent string from HTTP headers
            
        Returns:
            Dictionary containing parsed information
        """
        if not user_agent:
            return {
                'device_type': 'unknown',
                'browser': 'unknown',
                'browser_version': None,
                'os': 'unknown',
                'os_version': None,
                'platform': None,
            }
        
        user_agent_lower = user_agent.lower()
        
        # Detect device type
        device_type = 'desktop'
        for device, pattern in UserAgentParser.DEVICE_PATTERNS.items():
            if re.search(pattern, user_agent, re.IGNORECASE):
                device_type = device
                break
        
        # Detect browser
        browser = 'unknown'
        browser_version = None
        for browser_name, pattern in UserAgentParser.BROWSERS.items():
            match = re.search(pattern, user_agent)
            if match:
                browser = browser_name
                browser_version = match.group(1) if match.groups() else None
                break
        
        # Detect operating system
        os_name = 'unknown'
        os_version = None
        for os_key, pattern in UserAgentParser.OPERATING_SYSTEMS.items():
            match = re.search(pattern, user_agent)
            if match:
                os_name = os_key
                if match.groups():
                    os_version = match.group(1).replace('_', '.') if match.group(1) else None
                break
        
        # Platform detection
        platform = None
        if 'win' in user_agent_lower:
            platform = 'Windows'
        elif 'mac' in user_agent_lower:
            platform = 'Macintosh'
        elif 'linux' in user_agent_lower or 'x11' in user_agent_lower:
            platform = 'Linux'
        elif 'android' in user_agent_lower:
            platform = 'Android'
        elif 'ios' in user_agent_lower or 'iphone' in user_agent_lower or 'ipad' in user_agent_lower:
            platform = 'iOS'
        
        return {
            'device_type': device_type,
            'browser': browser,
            'browser_version': browser_version,
            'os': os_name,
            'os_version': os_version,
            'platform': platform,
        }


class NetworkActivityLogger:
    """
    Service for logging network activity details to the database.
    """
    
    @staticmethod
    def extract_ip_address(request: Request) -> tuple[Optional[str], Optional[str]]:
        """
        Extract IP address from request, checking X-Forwarded-For header first.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            Tuple of (ip_address, forwarded_for)
        """
        # Check X-Forwarded-For header (common with proxies/load balancers)
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first (client IP)
            ip_address = forwarded_for.split(',')[0].strip()
            return ip_address, forwarded_for
        
        # Fallback to direct client IP
        ip_address = request.client.host if request.client else None
        return ip_address, None
    
    @staticmethod
    def log_activity(
        request: Request,
        db: Session,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        company_id: Optional[str] = None,
        status_code: Optional[int] = None,
    ) -> Optional[NetworkActivityLog]:
        """
        Log network activity details to the database.
        
        Args:
            request: FastAPI Request object
            db: SQLAlchemy database session
            user_id: User identifier (if authenticated)
            session_id: Session identifier
            company_id: Company identifier
            status_code: HTTP response status code
            
        Returns:
            NetworkActivityLog instance if successful, None otherwise
        """
        try:
            # Extract IP addresses
            ip_address, forwarded_for = NetworkActivityLogger.extract_ip_address(request)
            
            # Extract user agent and parse it
            user_agent = request.headers.get('user-agent', '')
            parsed_ua = UserAgentParser.parse(user_agent)
            
            # Extract other request details
            endpoint = request.url.path
            method = request.method
            origin = request.headers.get('origin')
            referer = request.headers.get('referer')
            host = request.headers.get('host')
            
            # Generate unique request ID
            request_id = str(uuid.uuid4())
            
            # Create log entry
            log_entry = NetworkActivityLog(
                endpoint=endpoint[:255],  # Truncate if needed
                method=method[:10],
                ip_address=ip_address[:45] if ip_address else None,
                forwarded_for=forwarded_for[:255] if forwarded_for else None,
                user_agent=user_agent[:1000] if user_agent else None,  # Truncate long user agents
                device_type=parsed_ua['device_type'][:50] if parsed_ua['device_type'] else None,
                browser=parsed_ua['browser'][:100] if parsed_ua['browser'] else None,
                browser_version=parsed_ua['browser_version'][:50] if parsed_ua['browser_version'] else None,
                os=parsed_ua['os'][:100] if parsed_ua['os'] else None,
                os_version=parsed_ua['os_version'][:50] if parsed_ua['os_version'] else None,
                platform=parsed_ua['platform'][:50] if parsed_ua['platform'] else None,
                user_id=user_id[:255] if user_id else None,
                session_id=session_id[:255] if session_id else None,
                company_id=company_id[:100] if company_id else None,
                origin=origin[:255] if origin else None,
                referer=referer[:500] if referer else None,
                host=host[:255] if host else None,
                status_code=status_code,
                request_id=request_id[:100],
                created_at=datetime.utcnow()
            )
            
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)
            
            logger.debug(
                f"Network activity logged: request_id={request_id}, endpoint={endpoint}, "
                f"method={method}, ip={ip_address}, user_id={user_id}, device={parsed_ua['device_type']}, "
                f"browser={parsed_ua['browser']}, os={parsed_ua['os']}"
            )
            
            return log_entry
            
        except Exception as e:
            logger.error(f"Failed to log network activity: {str(e)}", exc_info=True)
            # Don't let logging failure break the request
            try:
                db.rollback()
            except:
                pass
            return None
    
    @staticmethod
    async def log_activity_async(
        request: Request,
        db: Session,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        company_id: Optional[str] = None,
        status_code: Optional[int] = None,
    ) -> Optional[NetworkActivityLog]:
        """
        Async wrapper for log_activity method.
        
        Args:
            request: FastAPI Request object
            db: SQLAlchemy database session
            user_id: User identifier (if authenticated)
            session_id: Session identifier
            company_id: Company identifier
            status_code: HTTP response status code
            
        Returns:
            NetworkActivityLog instance if successful, None otherwise
        """
        return NetworkActivityLogger.log_activity(
            request=request,
            db=db,
            user_id=user_id,
            session_id=session_id,
            company_id=company_id,
            status_code=status_code
        )


# Convenience function for easy import
async def log_network_activity(
    request: Request,
    db: Session,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    company_id: Optional[str] = None,
    status_code: Optional[int] = None,
) -> Optional[NetworkActivityLog]:
    """
    Convenience function to log network activity.
    
    Args:
        request: FastAPI Request object
        db: SQLAlchemy database session
        user_id: User identifier (if authenticated)
        session_id: Session identifier
        company_id: Company identifier
        status_code: HTTP response status code
        
    Returns:
        NetworkActivityLog instance if successful, None otherwise
    """
    return await NetworkActivityLogger.log_activity_async(
        request=request,
        db=db,
        user_id=user_id,
        session_id=session_id,
        company_id=company_id,
        status_code=status_code
    )

