# error_notifier/email_notifier.py
import os
import traceback
import asyncio
import json
import ssl
from typing import Optional, Dict, Any
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from app.utils.logger import logger

# DEVELOPMENT ONLY: Disable SSL verification for macOS
# This fixes "CERTIFICATE_VERIFY_FAILED" errors on macOS
# TODO: For production, use proper SSL certificates instead
import urllib.request
ssl._create_default_https_context = ssl._create_unverified_context

EXCEPTION_NOTIFIER_API_KEY = os.getenv("EXCEPTION_NOTIFIER_API_KEY")
EXCEPTION_NOTIFIER_SENDER = os.getenv("EXCEPTION_NOTIFIER_SENDER")
EXCEPTION_NOTIFIER_RECIPIENT = os.getenv("EXCEPTION_NOTIFIER_RECIPIENTS", "").split(",")

# GitHub repository configuration (can be overridden per call)
DEFAULT_GITHUB_OWNER = os.getenv("GITHUB_REPOSITORY_OWNER", "w3villa")
DEFAULT_GITHUB_REPO = os.getenv("GITHUB_REPOSITORY_NAME", "kivo_agent")
ENABLE_AI_ANALYSIS = os.getenv("ENABLE_AI_ERROR_ANALYSIS", "true").lower() == "true"


async def send_exception_email_async(
    error: Exception, 
    context: str = "No context provided", 
    session_id: Optional[str] = None, 
    origin: Optional[str] = None, 
    company_id: Optional[int] = None, 
    network_details: Optional[Dict[str, Any]] = None,
    file_path: Optional[str] = None,
    repository_owner: Optional[str] = None,
    repository_name: Optional[str] = None,
    enable_ai_analysis: Optional[bool] = None
):
    """
    Send error email using SendGrid with optional AI-powered error analysis.
    
    This function can automatically analyze errors using the GitHub Error Analysis Agent
    and include actionable solutions directly in the error notification email.
    
    Args:
        error: The exception that occurred
        context: Context information about the error
        session_id: Session identifier
        origin: Request origin
        company_id: Company identifier
        network_details: Dict with network info (ip_address, device_type, browser, os, user_agent)
        file_path: Path to the file where error occurred (for GitHub analysis)
        repository_owner: GitHub repository owner (defaults to env var)
        repository_name: GitHub repository name (defaults to env var)
        enable_ai_analysis: Whether to run AI analysis (defaults to env var ENABLE_AI_ERROR_ANALYSIS)
        
    Example:
        ```python
        # In your error handler
        try:
            result = risky_operation()
        except Exception as e:
            await send_exception_email_async(
                error=e,
                context="Failed in risky_operation",
                session_id="session_123",
                file_path="app/services/my_service.py",  # AI will analyze this file
                enable_ai_analysis=True  # Get AI-powered solutions
            )
        ```
    """
    if not EXCEPTION_NOTIFIER_API_KEY:
        logger.warning("SendGrid API key not set.")
        return

    # Determine if AI analysis should run
    should_analyze = enable_ai_analysis if enable_ai_analysis is not None else ENABLE_AI_ANALYSIS
    
    # Get repository info
    repo_owner = repository_owner or DEFAULT_GITHUB_OWNER
    repo_name = repository_name or DEFAULT_GITHUB_REPO
    
    subject_parts = [f"Error: {type(error).__name__}"]
    if session_id:
        subject_parts.append(f"Session ID- {session_id}")
    if company_id:
        subject_parts.append(f"Company ID- {company_id}")
    if origin:
        subject_parts.append(f"Origin- {origin}")

    subject = " | ".join(subject_parts)
    error_trace = traceback.format_exc()
    
    # Build network details section
    network_info = ""
    if network_details:
        network_info = "<br><strong>Network Details:</strong><br>"
        if network_details.get('ip_address'):
            network_info += f"<strong>IP Address:</strong> {network_details['ip_address']}<br>"
        if network_details.get('device_type'):
            network_info += f"<strong>Device:</strong> {network_details['device_type']}<br>"
        if network_details.get('browser'):
            browser_info = network_details['browser']
            if network_details.get('browser_version'):
                browser_info += f" {network_details['browser_version']}"
            network_info += f"<strong>Browser:</strong> {browser_info}<br>"
        if network_details.get('os'):
            os_info = network_details['os']
            if network_details.get('os_version'):
                os_info += f" {network_details['os_version']}"
            network_info += f"<strong>Operating System:</strong> {os_info}<br>"
        if network_details.get('user_agent'):
            network_info += f"<strong>User Agent:</strong> {network_details['user_agent']}<br>"
    
    # AI-Powered Error Analysis Section
    ai_analysis_section = ""
    if should_analyze and file_path:
        try:
            logger.info(f"Running AI error analysis for {file_path}...")
            
            # Import here to avoid circular dependency
            from app.helpers.github_error_analysis_agent import analyze_error_with_github_context
            
            # Run AI analysis
            analysis_result = await analyze_error_with_github_context(
                error=error,
                error_context=context,
                session_id=session_id or "unknown",
                company_id=company_id,
                origin=origin,
                repository_owner=repo_owner,
                repository_name=repo_name,
                file_path=file_path,
                network_details=network_details
            )
            
            # Extract analysis text
            analysis = analysis_result.get("analysis", {})
            if isinstance(analysis, dict):
                analysis_text = analysis.get("analysis", "Analysis not available")
            else:
                analysis_text = str(analysis)
            
            # Format for HTML email
            ai_analysis_section = f"""
    <br><hr><br>
    <h2 style="color: #2563eb;">🤖 AI-POWERED ERROR ANALYSIS</h2>
    <div style="background-color: #f8fafc; padding: 20px; border-left: 4px solid #2563eb; font-family: 'Courier New', monospace;">
        <pre style="white-space: pre-wrap; word-wrap: break-word; font-size: 13px;">{analysis_text}</pre>
    </div>
    <p style="color: #64748b; font-size: 12px; margin-top: 10px;">
        <em>This analysis was generated by KIVO GitHub Error Analysis Agent using Google Gemini AI and GitHub MCP tools.</em>
    </p>
    <br><hr><br>
    """
            
            logger.info("AI error analysis completed successfully")
            
        except Exception as analysis_error:
            logger.error(f"AI analysis failed: {analysis_error}", exc_info=True)
            ai_analysis_section = f"""
    <br><hr><br>
    <h2 style="color: #dc2626;">⚠️ AI Analysis Error</h2>
    <p style="color: #64748b;">
        The AI-powered error analysis encountered an issue: {str(analysis_error)}<br>
        The basic error details are provided below.
    </p>
    <br><hr><br>
    """
    
    # Build email body
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
        <h1 style="color: #dc2626;">🔴 KIVO AGENT ERROR REPORT</h1>
        
        <div style="background-color: #fef2f2; padding: 15px; border-left: 4px solid #dc2626; margin: 20px 0;">
            <strong>Context:</strong><br>
            {context}
        </div>
        
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr style="background-color: #f1f5f9;">
                <td style="padding: 10px; border: 1px solid #e2e8f0;"><strong>Error Type:</strong></td>
                <td style="padding: 10px; border: 1px solid #e2e8f0;">{type(error).__name__}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #e2e8f0;"><strong>Error Message:</strong></td>
                <td style="padding: 10px; border: 1px solid #e2e8f0;">{str(error)}</td>
            </tr>
            {f'<tr style="background-color: #f1f5f9;"><td style="padding: 10px; border: 1px solid #e2e8f0;"><strong>File Path:</strong></td><td style="padding: 10px; border: 1px solid #e2e8f0;">{file_path}</td></tr>' if file_path else ''}
            {f'<tr><td style="padding: 10px; border: 1px solid #e2e8f0;"><strong>Session ID:</strong></td><td style="padding: 10px; border: 1px solid #e2e8f0;">{session_id}</td></tr>' if session_id else ''}
            {f'<tr style="background-color: #f1f5f9;"><td style="padding: 10px; border: 1px solid #e2e8f0;"><strong>Company ID:</strong></td><td style="padding: 10px; border: 1px solid #e2e8f0;">{company_id}</td></tr>' if company_id else ''}
            {f'<tr><td style="padding: 10px; border: 1px solid #e2e8f0;"><strong>Origin:</strong></td><td style="padding: 10px; border: 1px solid #e2e8f0;">{origin}</td></tr>' if origin else ''}
        </table>
        
        {f'<div style="margin: 20px 0;">{network_info}</div>' if network_info else ''}
        
        {ai_analysis_section}
        
        <div style="background-color: #f8fafc; padding: 15px; margin: 20px 0;">
            <strong>Traceback:</strong><br>
            <pre style="white-space: pre-wrap; word-wrap: break-word; font-size: 12px; background-color: #1e293b; color: #e2e8f0; padding: 15px; border-radius: 5px; overflow-x: auto;">{error_trace}</pre>
        </div>
        
        <div style="color: #64748b; font-size: 11px; border-top: 1px solid #e2e8f0; padding-top: 10px; margin-top: 30px;">
            <p>Generated by KIVO Agent Error Notification System</p>
            {f'<p>Repository: {repo_owner}/{repo_name}</p>' if file_path else ''}
        </div>
    </div>
    """

    message = Mail(
        from_email=EXCEPTION_NOTIFIER_SENDER,
        to_emails=EXCEPTION_NOTIFIER_RECIPIENT,
        subject=subject,
        html_content=body
    )
    
    logger.info(f"Email subject: {subject}")
    if should_analyze and file_path:
        logger.info(f"Sending error email with AI analysis...")
    else:
        logger.info(f"Sending error email (AI analysis disabled or no file_path)")

    try:
        sg = SendGridAPIClient(EXCEPTION_NOTIFIER_API_KEY)
        response = sg.send(message)
        logger.info(f"Error email sent successfully with status code: {response.status_code}")
    except Exception as send_error:
        logger.error(f"Failed to send error email: {send_error}")
        logger.error(f"SendGrid API Key (first 10 chars): {EXCEPTION_NOTIFIER_API_KEY[:10] if EXCEPTION_NOTIFIER_API_KEY else 'NOT SET'}")
        logger.error(f"Sender: {EXCEPTION_NOTIFIER_SENDER}")
        logger.error(f"Recipients: {EXCEPTION_NOTIFIER_RECIPIENT}")
        # Log more details if available
        if hasattr(send_error, 'body'):
            logger.error(f"SendGrid error body: {send_error.body}")


def send_exception_email(
    error: Exception, 
    context: str = "No context provided", 
    session_id: Optional[str] = None, 
    origin: Optional[str] = None, 
    company_id: Optional[int] = None, 
    network_details: Optional[Dict[str, Any]] = None,
    file_path: Optional[str] = None,
    repository_owner: Optional[str] = None,
    repository_name: Optional[str] = None,
    enable_ai_analysis: Optional[bool] = None
):
    """
    Synchronous wrapper for send_exception_email_async.
    
    For backward compatibility with existing code that calls this synchronously.
    Creates an event loop and runs the async version.
    
    Args:
        Same as send_exception_email_async
        
    Note:
        This function will try to use an existing event loop if available,
        otherwise it creates a new one. For better performance in async contexts,
        use send_exception_email_async directly.
    """
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, schedule as a task
            asyncio.create_task(send_exception_email_async(
                error=error,
                context=context,
                session_id=session_id,
                origin=origin,
                company_id=company_id,
                network_details=network_details,
                file_path=file_path,
                repository_owner=repository_owner,
                repository_name=repository_name,
                enable_ai_analysis=enable_ai_analysis
            ))
        else:
            # Run in the existing loop
            loop.run_until_complete(send_exception_email_async(
                error=error,
                context=context,
                session_id=session_id,
                origin=origin,
                company_id=company_id,
                network_details=network_details,
                file_path=file_path,
                repository_owner=repository_owner,
                repository_name=repository_name,
                enable_ai_analysis=enable_ai_analysis
            ))
    except RuntimeError:
        # No event loop exists, create a new one
        asyncio.run(send_exception_email_async(
            error=error,
            context=context,
            session_id=session_id,
            origin=origin,
            company_id=company_id,
            network_details=network_details,
            file_path=file_path,
            repository_owner=repository_owner,
            repository_name=repository_name,
            enable_ai_analysis=enable_ai_analysis
        ))
