from typing import Dict, Any
from google.adk.tools.tool_context import ToolContext
from app.utils.logger import logger

def _extract_and_validate_context(tool_context: ToolContext) -> Dict[str, Any]:
    """Extract and validate session context information."""
    
    user_id = tool_context.state.get("user_id")
    session_id = tool_context.state.get("session_id")
    company_id = tool_context.state.get("company_id")
    origin = tool_context.state.get("origin")
    app_name = "performance_evaluation"
    
    # Validate required context
    missing_fields = []
    if not session_id:
        missing_fields.append("session_id")
    if not user_id:
        missing_fields.append("user_id")
    if not company_id:
        missing_fields.append("company_id")
    if not origin:
        missing_fields.append("origin")
    
    if missing_fields:
        logger.error(f"Context validation failed: Missing required context fields: {', '.join(missing_fields)}")
        return {
            "success": False,
            "error": f"Missing required context fields: {', '.join(missing_fields)}. This is a bug.",
            "message": "Required context not available"
        }
    
    logger.info(f"Context validation successful for user: {user_id}, session: {session_id}, company: {company_id}, origin: {origin}")
    return {
        "success": True,
        "user_id": user_id,
        "session_id": session_id,
        "company_id": company_id,
        "origin": origin,
        "app_name": app_name
    }


async def _validate_pipeline_prerequisites(tool_context: ToolContext) -> Dict[str, Any]:
    """Validate that required data exists in tool context."""
    
    # Check for validated performance data
    validated_performance_data = tool_context.state.get("validated_performance_data")
    if not validated_performance_data:
        logger.error("Pipeline prerequisite validation failed: No validated performance data found in session state")
        return {
            "success": False,
            "error": "No validated performance data found in session. Please run inject_performance_data first.",
            "message": "Performance data not available"
        }
    
    # Check for employee ID
    employee_id = tool_context.state.get("performance_evaluation_employee_id")
    if not employee_id:
        logger.error("Pipeline prerequisite validation failed: No employee ID found in session state")
        return {
            "success": False,
            "error": "No employee ID found in session. Please run inject_performance_data first.",
            "message": "Employee ID not available"
        }
    
    logger.info(f"Pipeline prerequisites validated successfully for employee: {employee_id}")
    return {
        "success": True,
        "validated_performance_data": validated_performance_data,
        "employee_id": employee_id
    }


