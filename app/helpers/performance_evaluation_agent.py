from google.adk.tools.tool_context import ToolContext
from app.utils.logger import logger
from pydantic import ValidationError
from app.helpers.performance_eval.tools import inject_performance_data, run_performance_evaluation_pipeline, set_employee_id_from_name
from app.services.redis_common_state import save_session_data


async def run_performance_evaluation_pipeline_with_retry(tool_context: ToolContext, max_retries: int = 2):
    """Wrapper that retries the performance evaluation pipeline if JSON validation fails.

    Args:
        tool_context: ADK tool context.
        max_retries: Number of retries *after* the first attempt (default 2 => 3 total attempts).
    """
    attempt = 0
    last_error = None
    while attempt <= max_retries:
        try:
            return await run_performance_evaluation_pipeline(tool_context)
        except ValidationError as ve:
            # Only retry on JSON / schema validation errors
            msg = str(ve)
            retryable = (
                "json_invalid" in msg
                or "Field required" in msg
                or "value is not a valid" in msg
            )
            if not retryable or attempt == max_retries:
                raise
            attempt += 1
            logger.warning(
                f"Performance evaluation pipeline JSON validation failed (attempt {attempt}/{max_retries}). Retrying…"
            )
            last_error = ve
        except Exception as e:
            # Non-validation errors are propagated immediately
            raise
    # Should not reach here, but raise last error for clarity
    raise last_error


async def initiate_performance_evaluation_tools(company_id, app_name, origin):
    """
    Initialize performance evaluation tools for integration with HRMS agent.
    Returns a list of tools that can be added to the HRMS agent.
    """
    try:
        logger.info(f"Initializing performance evaluation tools for company: {company_id}, app: {app_name}, origin: {origin}")
        
        # Validate parameters
        if not company_id:
            logger.error("Cannot initialize tools: company_id is required")
            return []
        
        if not app_name:
            logger.error("Cannot initialize tools: app_name is required")
            return []
        
        if not origin:
            logger.error("Cannot initialize tools: origin is required")
            return []
        
        # Return the two tools: data injection and pipeline execution
        tools = [inject_performance_data, run_performance_evaluation_pipeline]
        
        logger.info(f"Performance evaluation tools initialized successfully: {len(tools)} tools available")
        return tools
        
    except Exception as e:
        logger.error(f"Error initializing performance evaluation tools for company {company_id}: {e}", exc_info=True)
        return []
