import os
import asyncio
from sqlalchemy import MetaData, Table, select
from app.utils.logger import logger
from app.services.session_event_cleaner import should_clean_session, clean_session, KEEP_LAST_N_USER_TURNS

WAIT_SECONDS = int(os.getenv("EVENT_CLEANUP_WAIT_SECONDS", "3600"))  
ENABLE_PERIODIC_CLEANUP = os.getenv("ENABLE_PERIODIC_CLEANUP", "true").lower() == "true"


async def periodic_cleanup_task():
    """
    Background task that periodically cleans up old events across all sessions.
    
    Runs every WAIT_SECONDS (default: 1 hour), checks all sessions, and cleans
    those exceeding KEEP_LAST_N_USER_TURNS limit. Errors in individual cleanups
    don't stop the overall process.
    
    Config: WAIT_SECONDS, ENABLE_PERIODIC_CLEANUP, KEEP_LAST_N_USER_TURNS
    """
    if not ENABLE_PERIODIC_CLEANUP:
        logger.info("Periodic event cleanup is disabled")
        return
    
    logger.info(f"Starting periodic event cleanup task (runs every {WAIT_SECONDS} seconds)")
    
    while True:
        try:
            await asyncio.sleep(WAIT_SECONDS)
            
            logger.info(f"Running periodic event cleanup (KEEP_LAST_N_USER_TURNS={KEEP_LAST_N_USER_TURNS})")
            
            # Get database session
            from app.services.my_sql_client import SessionLocal
            db = SessionLocal()
            
            try:
                # Reflect the events table (read-only access)
                metadata = MetaData()
                events_table = Table("events", metadata, autoload_with=db.bind)
                
                # Get all unique session_ids from events table
                stmt = select(events_table.c.session_id).distinct()
                result = db.execute(stmt)
                session_ids = [row[0] for row in result]
                
                logger.info(f"Found {len(session_ids)} unique sessions to check")
                
                # Check and clean each session that needs it
                cleaned_count = 0
                total_events_removed = 0
                total_events_backed_up = 0
                
                for session_id in session_ids:
                    try:
                        if should_clean_session(db, session_id):
                            result = clean_session(db, session_id)
                            
                            if result.get('status') == 'success':
                                cleaned_count += 1
                                events_stats = result.get('events_table', {})
                                total_events_removed += events_stats.get('removed', 0)
                                total_events_backed_up += events_stats.get('backed_up', 0)
                    
                    except Exception as e:
                        logger.error(f"Error cleaning session {session_id}: {e}")
                        continue
                
                logger.info(
                    f"\nPeriodic cleanup completed:"
                    f"\n  - Sessions cleaned: {cleaned_count}"
                    f"\n  - Events removed: {total_events_removed}"
                    f"\n  - Events backed up: {total_events_backed_up}"
                )
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in periodic cleanup task: {e}", exc_info=True)
            # Continue the loop even if there's an error

def start_periodic_cleanup():
    """
    Start the periodic event cleanup background task.
    Config: ENABLE_PERIODIC_CLEANUP, EVENT_CLEANUP_WAIT_SECONDS
    """
    if not ENABLE_PERIODIC_CLEANUP:
        logger.info("Periodic event cleanup is disabled")
        return
    
    asyncio.create_task(periodic_cleanup_task())
    logger.info(f"✓ Periodic event cleanup scheduled (every {WAIT_SECONDS} seconds)")

