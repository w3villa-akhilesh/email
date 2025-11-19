from app.utils.logger import logger
from app.utils.agent_transfer_handler import transfer_handler
from typing import Tuple, Dict, Any
import litellm

async def get_final_agent_response(runner, user_id, session_id, content, company_id: int = None, current_agent: str = None, session_context: Dict[str, Any] = None) -> Tuple[str, str]:
    """
    Run the agent and extract the final response text.
    """
    final_response_text = "no response received"

    try:
        first_message_event_id = None
        invocation_id = None
        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
            invocation_id = event.invocation_id
            if event.id and first_message_event_id is None:
                first_message_event_id = event.id
            
            if event.content and event.content.parts:
                response_text = event.content.parts[0].text
                if event.get_function_calls():
                    logger.debug(f"Function Call from {event.author} as {event.get_function_calls()}")
                if response_text:
                    logger.debug(f"Agent_name: {event.author} response: {response_text}")
                if event.is_final_response():
                    final_response_text = response_text
        return final_response_text, first_message_event_id , invocation_id

    except Exception as e:
        logger.error(f"Error while running agent: {e}", exc_info=True)
        
        # Check if this is the specific tool call error that requires session reset
        error_str = str(e)
        if (isinstance(e, (litellm.exceptions.BadRequestError, Exception)) and 
            "tool_calls" in error_str and 
            "must be followed by tool messages" in error_str and
            "did not have response messages" in error_str):
            logger.warning(f"Detected tool call sequence error for session {session_id}: {error_str}")
            return "TOOL_CALL_ERROR_RETRY_NEEDED", first_message_event_id, invocation_id
        
        # Handle agent transfer errors gracefully
        if transfer_handler.is_agent_not_found_error(error_str):
            logger.warning(f"Agent transfer error detected: {error_str}")
            
            # Handle the error gracefully
            error_response = transfer_handler.handle_agent_transfer_error(
                error_message=error_str,
                current_agent=current_agent or "unknown",
                company_id=company_id,
                session_context=session_context
            )
            
            if error_response['should_handle']:
                logger.info(f"Providing graceful response for agent transfer error: {error_response['response_message']}")
                return error_response['response_message'], first_message_event_id, invocation_id
            else:
                # Fallback to generic message
                return "I'll help you with your query. Please provide more details about what you need assistance with.", first_message_event_id, invocation_id
        
        return "Error occurred while processing response", first_message_event_id, invocation_id

    finally:
        logger.info(f"Runner closed for invocation_id: {invocation_id}")
