from app.utils.logger import logger
from typing import Tuple
import litellm

async def get_final_agent_response(runner, user_id, session_id, content) -> Tuple[str, str]:
    """
    Run the agent and extract the final response text.
    """
    final_response_text = "no response received"

    try:
        first_message_event_id = None
        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
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
        return final_response_text, first_message_event_id

    except Exception as e:
        logger.error(f"Error while running agent: {e}", exc_info=True)
        
        # Check if this is the specific tool call error that requires session reset
        error_str = str(e)
        if (isinstance(e, (litellm.exceptions.BadRequestError, Exception)) and 
            "tool_calls" in error_str and 
            "must be followed by tool messages" in error_str and
            "did not have response messages" in error_str):
            logger.warning(f"Detected tool call sequence error for session {session_id}: {error_str}")
            return "TOOL_CALL_ERROR_RETRY_NEEDED", first_message_event_id
        
        if "Agent" in error_str and "not found in the agent tree" in error_str:
            logger.warning(f"Unknown agent transfer requested: {error_str}")
            return "You're not authorized to access this agent.", first_message_event_id
        
        return "Error occurred while processing response", first_message_event_id

    finally:
        logger.info("Runner closed")
