"""
Common WebSocket utility functions for IATS and Workplace agents.

This module contains shared functionality to avoid code duplication between
different WebSocket handlers.
"""

import json
# import logging
from typing import Dict, Any, Optional, Tuple
from fastapi import WebSocket
from app.socket.connect import manager
from app.services.my_sql_client import get_db
from app.services.chat_attachments import chat_attachments_service
from app.utils.logger import logger
from app.services.state_session_manager import (
    get_user_session_details,
    list_user_sessions,
    rename_chatname,
    search_chat_history,
)
from app.models.db_models import UserFeedback, ChatAttachments
from app.services.notification.notification_helpers import (
    clear_all_notification,
    handle_fetch_all_notifications,
    mark_all_notifications_as_read,
    mark_notification_as_read,
)
from app.services.edit_conversation import remove_conversation_included_from_event, delete_session

# logger = logging.getLogger(__name__)
from app.utils.logger import logger

async def handle_notification_actions(
    action: str,
    request_data_dict: Dict[str, Any],
    user_id: str,
    websocket: WebSocket,
    app_name: str,
) -> None:
    """
    Handle notification-related WebSocket actions.
    
    Args:
        action: The notification action to perform
        request_data_dict: The request data dictionary
        user_id: The user ID
        websocket: The WebSocket connection object
        app_name: The application name for notification context
    """
    logger.info(f"Processing notification action '{action}' for user {user_id}")
    
    if action == "get_all_notifications":
        page = int(request_data_dict.get("page", 1))
        page_size = int(request_data_dict.get("page_size", 10))
        logger.debug(f"Fetching notifications for user {user_id}, page {page}, size {page_size}")
        
        all_notifications = await handle_fetch_all_notifications(
            user_id, page=page, page_size=page_size, app_name=app_name
        )
        await manager.broadcast_json_to_user(
            user_id,
            {
                "action": "get_all_notifications",
                "status": "success",
                "notifications": all_notifications
            },
            app_name=app_name
        )
        logger.info(f"Successfully fetched {len(all_notifications) if isinstance(all_notifications, list) else 0} notifications for user {user_id}")
    
    elif action == "mark_as_read":
        message_id = request_data_dict.get("message_id")
        if not message_id:
            logger.warning(f"Missing message_id for mark_as_read action from user {user_id}")
            await manager.send_json(websocket, {
                "action": "mark_as_read",
                "status": "failure",
                "message": "Please provide message_id to mark as read."
            })
            return
        
        logger.debug(f"Marking message {message_id} as read for user {user_id}")
        response = await mark_notification_as_read(message_id)
        await manager.broadcast_json_to_user(
            user_id,
            {
                "action": "mark_as_read",
                "status": "success",
                "response": response
            },
            app_name=app_name
        )
        logger.info(f"Successfully marked message {message_id} as read for user {user_id}")
        return
    
    elif action == "clear_all_notification":
        logger.info(f"Clearing all notifications for user {user_id}")
        response = await clear_all_notification(app_name=app_name)
        await manager.broadcast_json_to_user(
            user_id,
            {
                "action": "clear_all_notification",
                "response": response,
            },
            app_name=app_name
        )
        logger.info(f"Successfully cleared all notifications for user {user_id}")
        return
    
    elif action == "mark_as_read_all":
        logger.info(f"Marking all notifications as read for user {user_id}")
        unread_notification = await mark_all_notifications_as_read(app_name=app_name)
        await manager.broadcast_json_to_user(
            user_id,
            {
                "status": "success",
                "action": "mark_as_read_all",
                "response": unread_notification,
            },
            app_name=app_name
        )
        logger.info(f"Successfully marked all notifications as read for user {user_id}")
        return


async def handle_session_management_actions(
    action: str,
    request_data_dict: Dict[str, Any],
    user_id: str,
    websocket: WebSocket,
    app_name: str,
) -> None:
    """
    Handle session management WebSocket actions.
    
    Args:
        action: The session management action to perform
        request_data_dict: The request data dictionary
        user_id: The user ID
        websocket: The WebSocket connection object
        app_name: The application name
    """
    logger.info(f"Processing session management action '{action}' for user {user_id}")
    
    if action == "get_all_chats":
        page = int(request_data_dict.get("page", 1))
        limit = int(request_data_dict.get("limit", 50))

        if not user_id:
            logger.warning(f"Missing user_id for get_all_chats action")
            await manager.send_json(websocket, {
                "status": "error",
                "message": "user_id is required to fetch chat names."
            })
            return

        logger.info(f"Fetching chat names: user_id={user_id}, page={page}, limit={limit}")

        # Calculate offset for pagination
        offset = (page - 1) * limit

        # Obtain a database session
        db_gen = get_db()
        db = next(db_gen)
        try:
            sessions_data = {
                "status": "success",
                "action": "get_all_chats",
                "data": {
                    "user_id": user_id,
                    "chats": list_user_sessions(db, user_id, limit, offset, app_name),                                   
                }
            }
            logger.info(f"Successfully fetched {len(sessions_data['data']['chats'])} chats for user {user_id}")
        finally:
            try:
                db_gen.close()
            except Exception:
                pass

        await manager.send_json(websocket, sessions_data)
    
    elif action == "get_chats_details":
        chat_session_id = request_data_dict.get("chat_session_id")
        if not chat_session_id:
            raise ValueError("chat_session_id is required in the request data.")
        
        page = int(request_data_dict.get("page", 1))
        limit = int(request_data_dict.get("limit", 50))

        if not user_id or not chat_session_id:
            logger.warning(f"Missing required parameters for get_chats_details: user_id={user_id}, chat_session_id={chat_session_id}")
            await manager.send_json(websocket, {
                "status": "error",
                "message": "user_id and session_id are required to fetch chat details."
            })
            return

        logger.info(f"Fetching chat details: user_id={user_id}, session_id={chat_session_id}, page={page}, limit={limit}")
        
        # Calculate offset for pagination
        offset = (page - 1) * limit

        # Obtain a database session
        db_gen = get_db()
        db = next(db_gen)
        try:
            history_details = get_user_session_details(
                db=db,
                user_id=user_id,
                session_id=chat_session_id,
                limit=limit,
                offset=offset,
                app_name=app_name
            )
            
            # Collect all event_ids from history
            event_ids = [msg.get("event_id") for msg in history_details.get("history", []) if msg.get("event_id")]
            
            # Fetch all feedback for messages in this session and history
            feedback_dict = {}
            if event_ids:
                feedback_list = db.query(UserFeedback).filter(
                    UserFeedback.session_id == chat_session_id,
                    UserFeedback.message_id.in_(event_ids)
                ).all()
                
                # Create a mapping of message_id to feedback
                for feedback in feedback_list:
                    feedback_dict[feedback.message_id] = {
                        "thumbs_up": feedback.thumbs_up,
                        "thumbs_down": feedback.thumbs_down
                    }
            
            # Fetch image attachments and add feedback for each message in the history
            for message in history_details.get("history", []):
                event_id = message.get("event_id")
                message_role = message.get("role")
                
                if event_id:
                    # Add image attachments
                    attachments = chat_attachments_service.get_attachments_by_message(
                        db=db,
                        chat_session_id=chat_session_id,
                        message_id=event_id,
                        user_id=user_id
                    )
                    # Add image URL as string (first image only)
                    message["image_url"] = attachments[0]["s3_url"] if attachments and len(attachments) > 0 else None
                    
                    # Add feedback information only for assistant messages
                    if message_role == "assistant":
                        if event_id in feedback_dict:
                            message["feedback"] = feedback_dict[event_id]
                        else:
                            # Initialize feedback fields even if no feedback exists
                            message["feedback"] = {
                                "thumbs_up": False,
                                "thumbs_down": False
                            }
            
            logger.info(f"Successfully fetched chat details for session {chat_session_id} with image attachments and feedback")
        finally:
            try:
                db_gen.close()
            except Exception:
                pass
        
        message = {
            "status": "success",
            "action": "get_chats_details",
            "data": {
                "user_id": user_id,
                "chats_details": history_details
            }
        }
        await manager.send_json(websocket, message)

    elif action == "search_chat_history":
        query = request_data_dict.get("query")
        page = int(request_data_dict.get("page", 1))
        limit = int(request_data_dict.get("limit", 50))

        if not user_id or not query:
            logger.warning(f"Missing required parameters for search_chat_history: user_id={user_id}, query={query}")
            await manager.send_json(websocket, {
                "status": "error",
                "message": "user_id and query are required to search chat history."
            })
            return

        logger.info(f"Searching chat history: user_id={user_id}, query='{query[:100]}...', page={page}, limit={limit}")

        # Calculate offset for pagination
        offset = (page - 1) * limit

        # Obtain a database session
        db_gen = get_db()
        db = next(db_gen)
        try:
            search_results = search_chat_history(db, user_id, query, limit, offset, app_name)
            logger.info(f"Search completed, found {len(search_results) if isinstance(search_results, list) else 0} results for user {user_id}")
        finally:
            try:
                db_gen.close()
            except Exception:
                pass
        
        message = {
            "status": "success",
            "action": "search_chat_history",
            "data": {
                "user_id": user_id,
                "search_results": search_results
            }
        }
        await manager.send_json(websocket, message)
        
    elif action == "rename_chat":
        chat_session_id = request_data_dict.get("chat_session_id")
        if not chat_session_id:
            raise ValueError("chat_session_id is required in the request data.")
        
        new_chat_name = request_data_dict.get("new_chat_name")

        if not user_id or not chat_session_id or not new_chat_name:
            logger.warning(f"Missing required parameters for rename_chat: user_id={user_id}, chat_session_id={chat_session_id}, new_chat_name={new_chat_name}")
            await manager.broadcast_json_to_user(user_id, {
                "status": "error",
                "message": "user_id, session_id, and chat_name are required to rename chat."
            })
            return

        logger.info(f"Renaming chat: user_id={user_id}, session_id={chat_session_id}, new_chat_name='{new_chat_name}'")

        # Obtain a database session
        db_gen = get_db()
        db = next(db_gen)
        try:
            rename_result = rename_chatname(db, user_id, chat_session_id, new_chat_name, app_name)
            logger.info(f"Successfully renamed chat {chat_session_id} to '{new_chat_name}' for user {user_id}")
        except Exception as e:
            logger.error(f"Error renaming chat {chat_session_id} for user {user_id}: {e}", exc_info=True)
            rename_result = {
                "status": "error",
                "message": f"Failed to rename chat: {str(e)}"
            }
        finally:
            try:
                db_gen.close()
            except Exception:
                pass
        
        message = {
            "status": "success",
            "action": "rename_chat",
            "data": {
                "user_id": user_id,
                "rename_result": rename_result
            }
        }
        await manager.broadcast_json_to_user(user_id, message, app_name=app_name)

async def handle_thumbs_up_down_actions(
    action: str,
    request_data_dict: Dict[str, Any],
    user_id: str,
    websocket: WebSocket,
    app_name: str,
    origin: str,
    company_id: Optional[str],
) -> None:
    """
    Handle thumbs up/down/clear_feedback actions.

    Args:
        action: The thumbs up/down action to perform
        request_data_dict: The request data dictionary
        user_id: The user ID
        websocket: The WebSocket connection object
        app_name: The application name
    """
    logger.info(f"Processing thumbs up/down action '{action}' for user {user_id}")
    logger.debug(f"process of handle thumbs up/down action ------------------------------------------------>")

    message_id = request_data_dict.get("message_id")
    if not message_id:
        logger.warning(f"Missing message_id for {action} action from user {user_id}")
        await manager.send_json(websocket, {
            "status": "error",
            "message": "message_id is required for this action."
        })
        return

    if action == "thumbs_up":
        logger.debug(f"Thumbs up message {message_id} for user {user_id}")
        result = await thumbs_up_message(
            message_id,
            user_id,
            app_name,
            chat_session_id=request_data_dict.get("chat_session_id") or request_data_dict.get("session_id"),
            company_id=company_id,
            origin=origin,
        )
        await manager.send_json(websocket, result)
        logger.info(f"Successfully thumbs up message {message_id} for user {user_id}")
    elif action == "thumbs_down":
        logger.debug(f"Thumbs down message {message_id} for user {user_id}")
        result = await thumbs_down_message(
            message_id,
            user_id,
            app_name,
            chat_session_id=request_data_dict.get("chat_session_id") or request_data_dict.get("session_id"),
            company_id=company_id,
            origin=origin,
        )
        await manager.send_json(websocket, result)
        logger.info(f"Successfully thumbs down message {message_id} for user {user_id}")
    elif action == "clear_feedback":
        logger.debug(f"Clear feedback for message {message_id} for user {user_id}")
        result = await clear_feedback_message(
            message_id,
            user_id,
            app_name,
            chat_session_id=request_data_dict.get("chat_session_id") or request_data_dict.get("session_id"),
            company_id=company_id,
            origin=origin,
        )
        await manager.send_json(websocket, result)
        logger.info(f"Successfully cleared feedback for message {message_id} for user {user_id}")
    return


async def thumbs_up_message(
    message_id: str,
    user_id: str,
    app_name: str,
    chat_session_id: Optional[str] = None,
    company_id: Optional[str] = None,
    origin: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Persist a thumbs up feedback for a message into user_feedback table.
    If chat_session_id is not provided, try to derive it from chat_attachments.
    """
    db_gen = get_db()
    db = next(db_gen)
    try:
        # Determine session id
        session_id = chat_session_id
        if not session_id:
            attach = db.query(ChatAttachments).filter(
                ChatAttachments.message_id == message_id,
                ChatAttachments.user_id == user_id,
            ).first()
            session_id = attach.chat_session_id if attach else None

        if not session_id:
            logger.warning(f"Unable to determine session_id for message_id={message_id}, user_id={user_id}")
            return {"status": "error", "message": "session_id not found for message"}

        existing = db.query(UserFeedback).filter(
            UserFeedback.session_id == session_id,
            UserFeedback.message_id == message_id,
        ).first()

        if existing:
            existing.thumbs_up = True
            existing.thumbs_down = False
        else:
            feedback = UserFeedback(
                session_id=session_id,
                message_id=message_id,
                company_id=company_id,
                origin=origin,
                thumbs_up=True,
                thumbs_down=False,
            )
            db.add(feedback)
        db.commit()
        return {
            "status": "success",
            "action": "thumbs_up",
            "chat_session_id": session_id,
            "message_id": message_id,
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving thumbs up feedback: {e}", exc_info=True)
        return {"status": "error", "message": "Failed to save thumbs up"}
    finally:
        try:
            db_gen.close()
        except Exception:
            pass


async def thumbs_down_message(
    message_id: str,
    user_id: str,
    app_name: str,
    chat_session_id: Optional[str] = None,
    company_id: Optional[str] = None,
    origin: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Persist a thumbs down feedback for a message into user_feedback table.
    If chat_session_id is not provided, try to derive it from chat_attachments.
    """
    db_gen = get_db()
    db = next(db_gen)
    try:
        # Determine session id
        session_id = chat_session_id
        if not session_id:
            attach = db.query(ChatAttachments).filter(
                ChatAttachments.message_id == message_id,
                ChatAttachments.user_id == user_id,
            ).first()
            session_id = attach.chat_session_id if attach else None

        if not session_id:
            logger.warning(f"Unable to determine session_id for message_id={message_id}, user_id={user_id}")
            return {"status": "error", "message": "session_id not found for message"}

        existing = db.query(UserFeedback).filter(
            UserFeedback.session_id == session_id,
            UserFeedback.message_id == message_id,
        ).first()

        if existing:
            existing.thumbs_up = False
            existing.thumbs_down = True
        else:
            feedback = UserFeedback(
                session_id=session_id,
                message_id=message_id,
                company_id=company_id,
                origin=origin,
                thumbs_up=False,
                thumbs_down=True,
            )
            db.add(feedback)
        db.commit()
        return {
            "status": "success",
            "action": "thumbs_down",
            "chat_session_id": session_id,
            "message_id": message_id,
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving thumbs down feedback: {e}", exc_info=True)
        return {"status": "error", "message": "Failed to save thumbs down"}
    finally:
        try:
            db_gen.close()
        except Exception:
            pass


async def clear_feedback_message(
    message_id: str,
    user_id: str,
    app_name: str,
    chat_session_id: Optional[str] = None,
    company_id: Optional[str] = None,
    origin: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Delete a feedback entry for a message from the user_feedback table.
    If chat_session_id is not provided, try to derive it from chat_attachments.
    Deletes the entry matching message_id and company_id.
    """
    db_gen = get_db()
    db = next(db_gen)
    try:
        # Determine session id
        session_id = chat_session_id
        if not session_id:
            attach = db.query(ChatAttachments).filter(
                ChatAttachments.message_id == message_id,
                ChatAttachments.user_id == user_id,
            ).first()
            session_id = attach.chat_session_id if attach else None

        if not session_id:
            logger.warning(f"Unable to determine session_id for message_id={message_id}, user_id={user_id}")
            return {"status": "error", "message": "session_id not found for message"}

        # Build query filter
        query_filter = [
            UserFeedback.session_id == session_id,
            UserFeedback.message_id == message_id,
        ]
        
        # Add company_id filter if provided
        if company_id:
            query_filter.append(UserFeedback.company_id == str(company_id))
        else:
            # If company_id is None/null, match entries where company_id is also None/null
            query_filter.append(UserFeedback.company_id.is_(None))

        # Find and delete the feedback entry
        existing = db.query(UserFeedback).filter(*query_filter).first()

        if existing:
            db.delete(existing)
            db.commit()
            logger.info(f"Deleted feedback entry for message_id={message_id}, company_id={company_id}, session_id={session_id}")
            return {
                "status": "success",
                "action": "clear_feedback",
                "chat_session_id": session_id,
                "message_id": message_id,
                "company_id": company_id,
            }
        else:
            logger.warning(f"No feedback entry found to delete for message_id={message_id}, company_id={company_id}, session_id={session_id}")
            return {
                "status": "success",
                "action": "clear_feedback",
                "message": "No feedback entry found to delete",
                "chat_session_id": session_id,
                "message_id": message_id,
                "company_id": company_id,
            }
    except Exception as e:
        db.rollback()
        logger.error(f"Error clearing feedback: {e}", exc_info=True)
        return {"status": "error", "message": "Failed to clear feedback"}
    finally:
        try:
            db_gen.close()
        except Exception:
            pass

async def handle_conversation_actions(
    action: str,
    request_data_dict: Dict[str, Any],
    user_id: str,
    websocket: WebSocket,
    app_name: str,
) -> None:
    """
    Handle conversation-related WebSocket actions.
    
    Args:
        action: The conversation action to perform
        request_data_dict: The request data dictionary
        user_id: The user ID
        websocket: The WebSocket connection object
        app_name: The application name
    """
    logger.info(f"Processing conversation action '{action}' for user {user_id}")
    logger.debug(f"process of handle chat action ------------------------------------------------>")
    
    if action == "remove_conversation_history_from_event":
        chat_session_id = request_data_dict.get("chat_session_id")
        event_id = request_data_dict.get("event_id")
        logger.debug(f"the action ------------------------------------------> {action}")

        if not all([user_id, event_id]):
            logger.warning(f"Missing required parameters for remove_conversation_history_from_event: user_id={user_id}, event_id={event_id}")
            await manager.send_json(websocket, {
                "action": "remove_conversation_history_from_event",
                "status": "error",
                "message": "user_id and event_id are required."
            })
            return

        logger.info(f"Removing conversation history from event: session_id={chat_session_id}, user_id={user_id}, event_id={event_id}")
        result = await remove_conversation_included_from_event(chat_session_id, user_id, event_id, app_name)
        await manager.send_json(websocket, result)
        logger.info(f"Successfully removed conversation history from event {event_id} for session {chat_session_id}")
        return
    
    elif action == "delete_session":
        chat_session_id_to_delete = request_data_dict.get("chat_session_id")
        logger.debug(f"the action is ---------------------------> {action}")

        if not chat_session_id_to_delete or not user_id:
            logger.warning(
                f"Missing required parameters for delete_session: "
                f"chat_session_id={chat_session_id_to_delete}, user_id={user_id}"
            )
            await manager.send_json(websocket, {
                "action": "delete_session",
                "status": "error",
                "message": "chat_session_id and user_id are required for deletion."
            })
            return

        logger.info(f"Deleting session: session_id={chat_session_id_to_delete}, user_id={user_id}")
        result = await delete_session(session_id=chat_session_id_to_delete, user_id=user_id, app_name=app_name)
        response = {
            "action": "delete_session",
            "status": "success",
            "chat_session_id": chat_session_id_to_delete,
            "message": "Session deleted successfully."
        }

        await manager.broadcast_json_to_user(user_id, response, app_name=app_name)
        logger.info(f"Successfully deleted session {chat_session_id_to_delete} for user {user_id}")
        return



def update_session_socket_ids(user_id: str, socket_session_id: str, app_name: str) -> None:
    """
    Update session data with socket session IDs.
    
    Args:
        user_id: The user ID
        socket_session_id: The socket session ID
        app_name: The application name
    """
    from app.services.redis_common_state import get_session_data, save_session_data

    raw_data = get_session_data(user_id, app_name)
    if raw_data is None:
        session_data = {}
    elif isinstance(raw_data, dict):
        session_data = raw_data
    else:
        session_data = json.loads(raw_data)

    session_set = set()
    if "socket_session_ids" in session_data:
        existing_list = json.loads(session_data["socket_session_ids"])
        session_set = set(existing_list)
    if socket_session_id not in session_set:
        session_set.add(socket_session_id)
    
    session_data["socket_session_ids"] = json.dumps(list(session_set))
    save_session_data(user_id, session_data, app_name)
