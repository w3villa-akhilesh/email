import logging
from google.adk.sessions import DatabaseSessionService
from app.services.my_sql_client import create_db_url
from app.services.s3_service import s3_service
import json
from app.models.db_models import SessionHistory, UserSession, ChatAttachments


class SessionEventEditor:
    def __init__(self, session_service: DatabaseSessionService):
        self.session_service = session_service
        self.db_engine = session_service.db_engine
        self.database_session_factory = session_service.database_session_factory

    def delete_events_from(self, app_name, user_id, session_id, event_id, preserve_current_message_attachments=False):
        """
        Delete all events from the given event_id (inclusive) for the session.
        Also updates the corresponding SessionHistory and deletes associated chat attachments.
        """
        from google.adk.sessions.database_session_service import StorageEvent
        with self.database_session_factory() as session_factory:
            # Find the event by id only (id is unique)
            target_event = session_factory.query(StorageEvent).filter(
                StorageEvent.id == str(event_id)
            ).first()
            if not target_event:
                return False, "Target event not found"
            target_timestamp = target_event.timestamp

            # Get all event IDs that will be deleted to remove associated chat attachments
            events_to_delete = session_factory.query(StorageEvent.id).filter(
                StorageEvent.app_name == app_name,
                StorageEvent.user_id == user_id,
                StorageEvent.session_id == session_id,
                StorageEvent.timestamp >= target_timestamp
            ).all()
            
            event_ids_to_delete = [event.id for event in events_to_delete]
            logging.info(f"Found {len(event_ids_to_delete)} events to delete: {event_ids_to_delete}")

            # Delete chat attachments for events that will be deleted
            # Optionally preserve attachments for the current message if editing with new image
            deleted_attachments_count = 0
            s3_files_deleted_count = 0
            try:
                # Determine which event IDs should have their attachments deleted
                if preserve_current_message_attachments:
                    # Exclude the current event_id from attachment deletion
                    event_ids_for_attachment_deletion = [eid for eid in event_ids_to_delete if str(eid) != str(event_id)]
                    logging.info(f"Preserving attachments for current message {event_id}, deleting attachments for: {event_ids_for_attachment_deletion}")
                else:
                    # Delete attachments for all events including current
                    event_ids_for_attachment_deletion = event_ids_to_delete
                    logging.info(f"Deleting attachments for all events: {event_ids_for_attachment_deletion}")
                
                if event_ids_for_attachment_deletion:
                    # First, fetch the attachments to get S3 URLs before deleting from database
                    attachments_to_delete = session_factory.query(ChatAttachments).filter(
                        ChatAttachments.chat_session_id == session_id,
                        ChatAttachments.message_id.in_(event_ids_for_attachment_deletion),
                        ChatAttachments.user_id == user_id
                    ).all()
                    
                    # Delete files from S3 first
                    for attachment in attachments_to_delete:
                        if attachment.s3_url:
                            try:
                                success = s3_service.delete_file(attachment.s3_url)
                                if success:
                                    s3_files_deleted_count += 1
                                    logging.info(f"Successfully deleted S3 file: {attachment.s3_url}")
                                else:
                                    logging.warning(f"Failed to delete S3 file: {attachment.s3_url}")
                            except Exception as s3_error:
                                logging.error(f"Error deleting S3 file {attachment.s3_url}: {str(s3_error)}")
                    
                    # Now delete from database
                    deleted_attachments_count = session_factory.query(ChatAttachments).filter(
                        ChatAttachments.chat_session_id == session_id,
                        ChatAttachments.message_id.in_(event_ids_for_attachment_deletion),
                        ChatAttachments.user_id == user_id
                    ).delete(synchronize_session=False)
                            
                    logging.info(f"Deleted {deleted_attachments_count} chat attachments and {s3_files_deleted_count} S3 files for messages: {event_ids_for_attachment_deletion}")
                else:
                    logging.info("No attachments to delete (current message attachments preserved)")
            except Exception as e:
                logging.error(f"Error deleting chat attachments: {str(e)}", exc_info=True)
                # Continue with event deletion even if attachment deletion fails

            # Delete the events
            deleted = session_factory.query(StorageEvent).filter(
                StorageEvent.app_name == app_name,
                StorageEvent.user_id == user_id,
                StorageEvent.session_id == session_id,
                StorageEvent.timestamp >= target_timestamp
            ).delete(synchronize_session=False)
            logging.info(f"Deleted {deleted} ADK events from event_id {event_id} (inclusive)")
            
            # Also update SessionHistory
            session_history = session_factory.query(SessionHistory).filter(SessionHistory.session_id == session_id).first()
            if session_history and session_history.history:
                try:
                    history_list = json.loads(session_history.history)
                    
                    target_index = -1
                    for i, message in enumerate(history_list):
                        if message.get("event_id") == str(event_id):
                            target_index = i
                            break
                    
                    if target_index != -1:
                        truncated_history = history_list[:target_index]
                        session_history.history = json.dumps(truncated_history)
                        logging.info(f"Truncated SessionHistory for session_id={session_id} at event_id={event_id}")
                    else:
                        logging.warning(f"event_id {event_id} not found in SessionHistory for session_id={session_id}. History not updated.")
                except json.JSONDecodeError:
                    logging.error(f"Failed to parse SessionHistory for session_id={session_id}")
            else:
                logging.warning(f"SessionHistory not found or empty for session_id={session_id}. Not updating history.")

            session_factory.commit()
            return True, f"Deleted {deleted} events, {deleted_attachments_count} chat attachments, and {s3_files_deleted_count} S3 files from event_id {event_id} (inclusive)"

async def remove_conversation_included_from_event(session_id: str, user_id: str, event_id: str, app_name: str, preserve_current_message_attachments: bool = False):
    """
    Remove conversation events from a specific event_id (inclusive) for a session and user.
    
    Args:
        session_id: The chat session ID
        user_id: The user ID
        event_id: The event ID to start deletion from (inclusive)
        app_name: The application name
        preserve_current_message_attachments: If True, preserve attachments for the current message_id
    """
    verified_db_url = create_db_url()
    if not verified_db_url:
        msg = "Invalid database URL"
        logging.error(msg)
        return {"status": "error", "message": msg}

    try:
        session_service = DatabaseSessionService(db_url=verified_db_url)
        session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)

        if not session:
            return {"status": "error", "message": "Session not found"}

        editor = SessionEventEditor(session_service)
        success, msg = editor.delete_events_from(app_name, user_id, session_id, event_id, preserve_current_message_attachments)

        if success:
            logging.info(f"Successfully removed events for session {session_id} from event {event_id}")
            return {"status": "success", "message": msg}
        else:
            logging.warning(f"Failed to remove events for session {session_id} from event {event_id}: {msg}")
            return {"status": "error", "message": msg}
    except Exception as e:
        logging.error(f"An exception occurred in remove_iats_conversation_included_from_event: {e}", exc_info=True)
        return {"status": "error", "message": "An internal error occurred."}

async def delete_iats_session(session_id: str, user_id: str):
    """
    Deletes an entire iATS session for a user, including ADK events and session history.
    """
    app_name = "iats_sequential_flow"
    verified_db_url = create_db_url()
    if not verified_db_url:
        msg = "Invalid database URL"
        logging.error(msg)
        return {"status": "error", "message": msg}

    try:
        session_service = DatabaseSessionService(db_url=verified_db_url)

        session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
        if not session:
            return {"status": "error", "message": f"Session not found with session_id: {session_id}, user_id: {user_id}, app_name: {app_name}"}
        else:
            logging.info(f"Session found: {session}")
        # This will delete the StorageSession and cascade to StorageEvents
        await session_service.delete_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )
        logging.info(f"Successfully deleted ADK session {session_id} for user {user_id}")
        
        # Also delete from our custom tables in the same transaction
        with session_service.database_session_factory() as session_factory:
            # Delete chat attachments for the entire session
            deleted_attachments_count = 0
            s3_files_deleted_count = 0
            try:
                # First, fetch the attachments to get S3 URLs before deleting from database
                attachments_to_delete = session_factory.query(ChatAttachments).filter(
                    ChatAttachments.chat_session_id == session_id,
                    ChatAttachments.user_id == user_id
                ).all()
                
                # Delete files from S3 first
                for attachment in attachments_to_delete:
                    if attachment.s3_url:
                        try:
                            success = s3_service.delete_file(attachment.s3_url)
                            if success:
                                s3_files_deleted_count += 1
                                logging.info(f"Successfully deleted S3 file: {attachment.s3_url}")
                            else:
                                logging.warning(f"Failed to delete S3 file: {attachment.s3_url}")
                        except Exception as s3_error:
                            logging.error(f"Error deleting S3 file {attachment.s3_url}: {str(s3_error)}")
                
                # Now delete from database
                deleted_attachments_count = session_factory.query(ChatAttachments).filter(
                    ChatAttachments.chat_session_id == session_id,
                    ChatAttachments.user_id == user_id
                ).delete(synchronize_session=False)
                logging.info(f"Deleted {deleted_attachments_count} chat attachments and {s3_files_deleted_count} S3 files for session {session_id}")
            except Exception as e:
                logging.error(f"Error deleting chat attachments for session {session_id}: {str(e)}", exc_info=True)
                # Continue with other deletions even if attachment deletion fails
            
            # Delete from SessionHistory first to satisfy foreign key constraints
            deleted_history = session_factory.query(SessionHistory).filter(
                SessionHistory.session_id == session_id
            ).delete(synchronize_session=False)

            # Then delete from UserSession
            deleted_user_session = session_factory.query(UserSession).filter(
                UserSession.session_id == session_id,
                UserSession.user_id == user_id
            ).delete(synchronize_session=False)

            session_factory.commit()

            if deleted_user_session > 0 or deleted_history > 0:
                logging.info(f"Deleted session {session_id} from custom tables (UserSession: {deleted_user_session}, SessionHistory: {deleted_history}, ChatAttachments: {deleted_attachments_count}, S3 Files: {s3_files_deleted_count})")
            else:
                logging.warning(f"Session {session_id} not found in custom tables (UserSession/SessionHistory) for user {user_id}.")

        return {"status": "success", "message": f"Session {session_id} has been completely deleted."}
    except Exception as e:
        logging.error(f"An exception occurred in delete_iats_session: {e}", exc_info=True)
        return {"status": "error", "message": "An internal error occurred while deleting the session."}



async def delete_session(session_id: str, user_id: str, app_name:str = "iats_sequential_flow"):
    """
    Deletes an entire iATS session for a user, including ADK events and session history.
    """
    
    verified_db_url = create_db_url()
    if not verified_db_url:
        msg = "Invalid database URL"
        logging.error(msg)
        return {"status": "error", "message": msg}

    try:
        session_service = DatabaseSessionService(db_url=verified_db_url)

        session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
        if not session:
            return {"status": "error", "message": f"Session not found with session_id: {session_id}, user_id: {user_id}, app_name: {app_name}"}
        else:
            logging.info(f"Session found: {session}")
        # This will delete the StorageSession and cascade to StorageEvents
        await session_service.delete_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )
        logging.info(f"Successfully deleted ADK session {session_id} for user {user_id}")
        
        # Also delete from our custom tables in the same transaction
        with session_service.database_session_factory() as session_factory:
            # Delete chat attachments for the entire session
            deleted_attachments_count = 0
            s3_files_deleted_count = 0
            try:
                # First, fetch the attachments to get S3 URLs before deleting from database
                attachments_to_delete = session_factory.query(ChatAttachments).filter(
                    ChatAttachments.chat_session_id == session_id,
                    ChatAttachments.user_id == user_id
                ).all()
                
                # Delete files from S3 first
                for attachment in attachments_to_delete:
                    if attachment.s3_url:
                        try:
                            success = s3_service.delete_file(attachment.s3_url)
                            if success:
                                s3_files_deleted_count += 1
                                logging.info(f"Successfully deleted S3 file: {attachment.s3_url}")
                            else:
                                logging.warning(f"Failed to delete S3 file: {attachment.s3_url}")
                        except Exception as s3_error:
                            logging.error(f"Error deleting S3 file {attachment.s3_url}: {str(s3_error)}")
                
                # Now delete from database
                deleted_attachments_count = session_factory.query(ChatAttachments).filter(
                    ChatAttachments.chat_session_id == session_id,
                    ChatAttachments.user_id == user_id
                ).delete(synchronize_session=False)
                logging.info(f"Deleted {deleted_attachments_count} chat attachments and {s3_files_deleted_count} S3 files for session {session_id}")
            except Exception as e:
                logging.error(f"Error deleting chat attachments for session {session_id}: {str(e)}", exc_info=True)
                # Continue with other deletions even if attachment deletion fails
            
            # Delete from SessionHistory first to satisfy foreign key constraints
            deleted_history = session_factory.query(SessionHistory).filter(
                SessionHistory.session_id == session_id
            ).delete(synchronize_session=False)

            # Then delete from UserSession
            deleted_user_session = session_factory.query(UserSession).filter(
                UserSession.session_id == session_id,
                UserSession.user_id == user_id
            ).delete(synchronize_session=False)

            session_factory.commit()

            if deleted_user_session > 0 or deleted_history > 0:
                logging.info(f"Deleted session {session_id} from custom tables (UserSession: {deleted_user_session}, SessionHistory: {deleted_history}, ChatAttachments: {deleted_attachments_count}, S3 Files: {s3_files_deleted_count})")
            else:
                logging.warning(f"Session {session_id} not found in custom tables (UserSession/SessionHistory) for user {user_id}.")

        return {"status": "success", "message": f"Session {session_id} has been completely deleted."}
    except Exception as e:
        logging.error(f"An exception occurred in delete_iats_session: {e}", exc_info=True)
        return {"status": "error", "message": "An internal error occurred while deleting the session."}
