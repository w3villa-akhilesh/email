import os
import json
import threading
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import MetaData, Table, select, delete
from app.utils.logger import logger
from datetime import datetime

KEEP_LAST_N_USER_TURNS = max(0, int(os.getenv("KEEP_LAST_N_USER_TURNS", "4")))
AUTO_SESSION_CLEANUP = os.getenv("AUTO_SESSION_CLEANUP", "true").lower() == "true"


class EventRow:
    """Simple wrapper for event row data from table reflection"""
    def __init__(self, row):
        self.id = row.id
        self.app_name = row.app_name
        self.user_id = row.user_id
        self.session_id = row.session_id
        self.invocation_id = row.invocation_id
        self.author = row.author
        self.branch = row.branch if hasattr(row, 'branch') else None
        self.timestamp = row.timestamp
        self.content = row.content
        self.actions = row.actions
        self.long_running_tool_ids_json = row.long_running_tool_ids_json if hasattr(row, 'long_running_tool_ids_json') else None
        self.grounding_metadata = row.grounding_metadata if hasattr(row, 'grounding_metadata') else None
        self.partial = row.partial if hasattr(row, 'partial') else None
        self.turn_complete = row.turn_complete if hasattr(row, 'turn_complete') else None
        self.error_code = row.error_code if hasattr(row, 'error_code') else None
        self.error_message = row.error_message if hasattr(row, 'error_message') else None
        self.interrupted = row.interrupted if hasattr(row, 'interrupted') else None

def _identify_user_turn_sets(events: List) -> List[List]:
    """Group events into user turn sets (one user message + subsequent responses)."""
    if not events:
        return []
    
    event_sets = []
    current_set = []
    
    for event in events:
        author = event.author.lower() if event.author else ""
        
        if author == "user" and current_set:
            event_sets.append(current_set)
            current_set = [event]
        else:
            current_set.append(event)
    
    if current_set:
        event_sets.append(current_set)
    
    return event_sets

def should_clean_session(db: Session, session_id: str) -> bool:
    """Check if session needs cleanup (has more than KEEP_LAST_N_USER_TURNS turn sets)."""
    try:
        # Reflect the events table (read-only access)
        metadata = MetaData()
        events_table = Table("events", metadata, autoload_with=db.bind)
        
        # Query events for this session, ordered by timestamp
        stmt = select(events_table).where(
            events_table.c.session_id == session_id
        ).order_by(events_table.c.timestamp)
        
        result = db.execute(stmt)
        rows = result.fetchall()
        
        if not rows:
            return False
        
        # Convert rows to EventRow objects
        events = [EventRow(row) for row in rows]
        event_sets = _identify_user_turn_sets(events)
        
        if len(event_sets) > KEEP_LAST_N_USER_TURNS:
            logger.info(
                f"Session {session_id} has {len(event_sets)} user turn sets, "
                f"exceeding limit of {KEEP_LAST_N_USER_TURNS}"
            )
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking if session {session_id} needs cleaning: {e}")
        return False

def clean_session(db: Session, session_id: str) -> Dict[str, any]:
    """Clean session and return detailed results (status, stats, timestamp)."""
    logger.info(f"Starting cleanup for session {session_id}")
    
    try:
        # Import EventBackup ORM model
        from app.models.db_models import EventBackup
        
        # Reflect the events table (read-only access)
        metadata = MetaData()
        events_table = Table("events", metadata, autoload_with=db.bind)
        
        # Fetch all events for this session
        stmt = select(events_table).where(
            events_table.c.session_id == session_id
        ).order_by(events_table.c.timestamp)
        
        result = db.execute(stmt)
        rows = result.fetchall()
        
        # Convert rows to EventRow objects
        events = [EventRow(row) for row in rows]
        
        if not events:
            return {
                "session_id": session_id,
                "status": "success",
                "keep_last_n_user_turns": KEEP_LAST_N_USER_TURNS,
                "events_table": {"kept": 0, "removed": 0, "backed_up": 0},
                "timestamp": datetime.utcnow().isoformat()
            }
        
        original_count = len(events)
        event_sets = _identify_user_turn_sets(events)
        
        if not event_sets:
            logger.warning(f"No user turn sets found for session {session_id}")
            return {
                "session_id": session_id,
                "status": "success",
                "keep_last_n_user_turns": KEEP_LAST_N_USER_TURNS,
                "events_table": {"kept": original_count, "removed": 0, "backed_up": 0},
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Check if cleanup is needed
        if len(event_sets) <= KEEP_LAST_N_USER_TURNS:
            logger.info(
                f"Session {session_id}: No cleanup needed - "
                f"{len(event_sets)} turn sets within limit of {KEEP_LAST_N_USER_TURNS}"
            )
            return {
                "session_id": session_id,
                "status": "success",
                "keep_last_n_user_turns": KEEP_LAST_N_USER_TURNS,
                "events_table": {"kept": original_count, "removed": 0, "backed_up": 0},
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Determine which sets to keep/delete
        if KEEP_LAST_N_USER_TURNS == 0:
            sets_to_keep = []
            sets_to_delete = event_sets
        else:
            sets_to_keep = event_sets[-KEEP_LAST_N_USER_TURNS:]
            sets_to_delete = event_sets[:-KEEP_LAST_N_USER_TURNS]
        
        events_to_keep = [event for event_set in sets_to_keep for event in event_set]
        events_to_delete = [event for event_set in sets_to_delete for event in event_set]
        
        logger.info(
            f"Session {session_id}: Cleanup plan - "
            f"Keep {len(sets_to_keep)} turn sets ({len(events_to_keep)} events), "
            f"Delete {len(sets_to_delete)} turn sets ({len(events_to_delete)} events)"
        )
        
        # ATOMIC TRANSACTION: Backup + Delete
        try:
            # Backup events to events_backup table
            backed_up_count = 0
            for event in events_to_delete:
                content_data = event.content
                if isinstance(content_data, dict):
                    content_data = json.dumps(content_data)
                
                actions_data = getattr(event, 'actions', None)
                # Don't convert bytes to string - LargeBinary column expects bytes
                if actions_data and not isinstance(actions_data, (bytes, bytearray, memoryview, type(None))):
                    # Only convert if it's not already binary and not None
                    logger.warning(
                        f"Event {event.id}: actions field is {type(actions_data)}, expected bytes. "
                        f"Converting to JSON string for backup."
                    )
                    actions_data = json.dumps(actions_data).encode('utf-8')
                
                backup_event = EventBackup(
                    id=event.id,
                    app_name=event.app_name,
                    user_id=event.user_id,
                    session_id=event.session_id,
                    invocation_id=event.invocation_id,
                    author=event.author,
                    branch=getattr(event, 'branch', None),
                    timestamp=event.timestamp,
                    content=content_data,
                    actions=actions_data,
                    long_running_tool_ids_json=getattr(event, 'long_running_tool_ids_json', None),
                    grounding_metadata=getattr(event, 'grounding_metadata', None),
                    partial=getattr(event, 'partial', None),
                    turn_complete=getattr(event, 'turn_complete', None),
                    error_code=getattr(event, 'error_code', None),
                    error_message=getattr(event, 'error_message', None),
                    interrupted=getattr(event, 'interrupted', None),
                    backed_up_at=datetime.utcnow()
                )
                db.merge(backup_event)
                backed_up_count += 1
            
            logger.debug(f"Prepared {backed_up_count} events for backup in session {session_id}")
            
            # Delete old events from main events table
            event_ids_to_delete = [event.id for event in events_to_delete]
            
            if event_ids_to_delete:
                delete_stmt = delete(events_table).where(
                    events_table.c.id.in_(event_ids_to_delete)
                )
                result = db.execute(delete_stmt)
                removed_count = result.rowcount
            else:
                removed_count = 0
            
            logger.debug(f"Prepared {removed_count} events for deletion in session {session_id}")
            
            # Commit the transaction (backup + delete together)
            db.commit()
            
            logger.info(
                f"✓ Session {session_id} cleaned successfully: "
                f"Kept {len(events_to_keep)}/{original_count} events in {len(sets_to_keep)} turn sets, "
                f"Deleted {removed_count} events, Backed up {backed_up_count} events"
            )
            
            return {
                "session_id": session_id,
                "status": "success",
                "keep_last_n_user_turns": KEEP_LAST_N_USER_TURNS,
                "events_table": {
                    "kept": len(events_to_keep),
                    "removed": removed_count,
                    "backed_up": backed_up_count,
                    "user_turn_sets_kept": len(sets_to_keep),
                    "user_turn_sets_deleted": len(sets_to_delete)
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as transaction_error:
            logger.error(
                f"✗ Transaction failed for session {session_id}: {transaction_error}",
                exc_info=True
            )
            db.rollback()
            raise
        
    except Exception as e:
        logger.error(f"Error during session cleanup for {session_id}: {e}", exc_info=True)
        try:
            db.rollback()
        except:
            pass
        return {
            "session_id": session_id,
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

def integrate_with_session_update(db: Session, session_id: str) -> None:
    """Auto-cleanup hook for session updates. Runs cleanup in background thread if needed."""
    try:
        if not AUTO_SESSION_CLEANUP or not should_clean_session(db, session_id):
            return
        
        from app.services.my_sql_client import SessionLocal
        
        # Run cleanup in background thread with its own DB session
        def _cleanup_worker():
            db_thread = None
            try:
                db_thread = SessionLocal()
                
                # Check again and clean if needed
                if should_clean_session(db_thread, session_id):
                    result = clean_session(db_thread, session_id)
                    if result and result.get('status') == 'success':
                        events_removed = result.get('events_table', {}).get('removed', 0)
                        logger.info(f"Background cleanup completed for session {session_id}: removed {events_removed} events")
                        
            except Exception as e:
                logger.error(f"Error in background cleanup for session {session_id}: {e}", exc_info=True)
            finally:
                if db_thread:
                    db_thread.close()
        
        thread = threading.Thread(target=_cleanup_worker, daemon=True, name=f"cleanup-{session_id}")
        thread.start()
        logger.info(f"Started background cleanup thread for session {session_id}")
        
    except Exception as e:
        logger.error(f"Error starting background cleanup for session {session_id}: {e}")

def get_session_cleanup_stats(db: Session, session_id: str) -> Dict[str, Any]:
    """Get session cleanup eligibility and current state statistics."""
    try:
        from app.models.db_models import SessionHistory
        
        # Get session history info
        session_history = db.query(SessionHistory).filter_by(session_id=session_id).first()
        history_count = 0
        user_messages = 0
        assistant_messages = 0
        
        if session_history and session_history.history:
            history = json.loads(session_history.history)
            if isinstance(history, list):
                history_count = len(history)
                for item in history:
                    role = item.get("role", "")
                    if role == "user":
                        user_messages += 1
                    elif role == "assistant":
                        assistant_messages += 1
        
        # Get events table info
        events_count = 0
        events_user_count = 0
        events_model_count = 0
        
        try:
            # Reflect the events table (read-only access)
            metadata = MetaData()
            events_table = Table("events", metadata, autoload_with=db.bind)
            
            # Query events for this session
            stmt = select(events_table).where(events_table.c.session_id == session_id)
            result = db.execute(stmt)
            rows = result.fetchall()
            
            events_count = len(rows)
            
            for row in rows:
                if row.author and row.author.lower() == "user":
                    events_user_count += 1
                else:
                    events_model_count += 1
                    
        except Exception as e:
            logger.warning(f"Could not access events table for statistics: {e}")
        
        needs_cleanup = should_clean_session(db, session_id)
        
        return {
            "session_id": session_id,
            "keep_last_n_user_turns": KEEP_LAST_N_USER_TURNS,
            "needs_cleanup": needs_cleanup,
            "session_history": {
                "total_count": history_count,
                "user_messages": user_messages,
                "assistant_messages": assistant_messages
            },
            "events_table": {
                "total_count": events_count,
                "user_events": events_user_count,
                "model_events": events_model_count
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting session cleanup stats for {session_id}: {e}")
        return {
            "session_id": session_id,
            "error": str(e)
        }

def manual_session_cleanup(db: Session, session_id: str, force: bool = False) -> Dict[str, Any]:
    """Manually trigger session cleanup (force=True skips limit check)."""
    try:
        if force:
            logger.info(f"Force cleaning session {session_id}")
            return clean_session(db, session_id)
        
        # Check if cleanup is needed and clean
        if should_clean_session(db, session_id):
            return clean_session(db, session_id)
        else:
            return {
                "session_id": session_id,
                "status": "no_cleanup_needed",
                "message": f"Session has {KEEP_LAST_N_USER_TURNS} or fewer user turn sets",
                "keep_last_n_user_turns": KEEP_LAST_N_USER_TURNS
            }
                
    except Exception as e:
        logger.error(f"Error during manual cleanup for session {session_id}: {e}")
        return {
            "session_id": session_id,
            "status": "error",
            "message": str(e)
        }
