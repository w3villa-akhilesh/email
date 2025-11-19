from app.utils.logger import logger
import time
import asyncio
from app.services.redis_common_state import get_session_data
import json

def check_multiple_message(session_id:str)->bool:
    """
    Check for multiple queries in the session queue.
    
    Args:
        session_id (str): The session ID to check
        
    Returns:
        bool: True if multiple queries found (should block), False if single query (should proceed)
    """
    try:
        # Set this to False to allow normal processing, True to test blocking
        
        logger.info("checking for multiple messages")
        # Get session data from Redis
        session_data = get_session_data(session_id)
        if not session_data or "check_queries" not in session_data:
            logger.warning("check_multiple_message: No check_queries found in session data")
            return False  # No queries found, proceed normally
            
        # Parse queries from Redis
        queries = json.loads(session_data["check_queries"])
        logger.info("check_multiple_message: queries: %s", queries)
        
        if len(queries) > 1:
            logger.warning("check_multiple_message: Multiple queries found - BLOCKING execution")
            logger.warning(f"check_multiple_message: Found {len(queries)} queries in queue for session {session_id}")
            return True  # Multiple queries found, should block
        else:
            logger.info("check_multiple_message: Single query found - allowing normal processing")
            return False  # Single query, proceed normally
            
    except json.JSONDecodeError as e:
        logger.error(f"check_multiple_message: Error parsing queries JSON: {e}")
        return False  # On error, proceed normally
    except Exception as e:
        logger.error(f"check_multiple_message: Unexpected error: {e}", exc_info=True)
        return False  # On error, proceed normally

async def wait_for_single_query(session_id: str, query_uuid:str, max_wait_time: int = 30) -> bool:
    """
    Wait for multiple queries to be resolved until only one remains.
    
    Args:
        session_id (str): The session ID to check
        max_wait_time (int): Maximum time to wait in seconds (default: 30)
        
    Returns:
        bool: True if only one query remains, False if timeout
    """
    start_time = time.time()
    check_interval = 0.5  # Check every 0.5 seconds
    
    while time.time() - start_time < max_wait_time:
        try:
            # Get session data from Redis
            session_data = get_session_data(session_id)
            
            if not session_data or "check_queries" not in session_data:
                logger.info(f"No check_queries found for session {session_id} - proceeding")
                return True
                
            # Parse queries from Redis
            queries = json.loads(session_data["check_queries"])
            queries_count = len(queries)
            
            logger.info(f"Session {session_id} has {queries_count} queries in queue")
            
            # Fix race condition: Check if queries list is empty before accessing queries[0]
            if queries_count <= 0:
                logger.info(f"No queries found for session {session_id} - proceeding")
                return True
                
            first_query_index = queries[0].get("index", "")
            if queries_count <= 1 or first_query_index == query_uuid:
                logger.info(f"Single query remaining for session {session_id} - proceeding with execution")
                return True
                
            logger.info(f"Multiple queries ({queries_count}) found for session {session_id} - waiting...")
            await asyncio.sleep(check_interval)
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing queries JSON for session {session_id}: {e}")
            return True  # Proceed if there's a parsing error
        except Exception as e:
            logger.error(f"Error checking queries for session {session_id}: {e}", exc_info=True)
            return True  # Proceed if there's an unexpected error
    
    logger.warning(f"Timeout waiting for single query for session {session_id} - proceeding anyway")
    return False  # Timeout occurred
