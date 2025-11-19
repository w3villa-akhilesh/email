from fastapi import WebSocket
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from grpc import Status
from app.services.current_user_info import get_current_profile
from app.services.notification.notification_helpers import clear_all_notification, handle_fetch_all_notifications, mark_all_notifications_as_read, mark_notification_as_read
from app.services.redis_common_state import get_session_data, save_session_data
from app.socket.connect import WebSocketConnectionManager
from app.models.schema import InvokeAgentRequest
from app.helpers.iats import initiate_iats_agent
from app.socket.websocket_utils import update_session_socket_ids, handle_thumbs_up_down_actions
from app.utils.logger import logger
from app.services.invoke_agent import invoke_agent
from app.services.my_sql_client import get_db
from app.services.chat_attachments import chat_attachments_service
from app.services.vision_service import handle_vision_api
from app.services.edit_conversation import remove_conversation_included_from_event, delete_session
import json
import asyncio
import uuid
from app.socket.connect import manager
from app.services.state_session_manager import get_user_session_details, list_user_sessions, rename_chatname, search_chat_history
from app.models.db_models import UserFeedback
from pm_board_data.core.config import BASE_URL
import os 
from app.core.exceptions import LLMKeyNotSetException
from app.services.email_notifier import send_exception_email
from app.services.websocket_network_logger import log_websocket_connection

app_name = "iats_sequential_flow"

async def process_ws_message(data, websocket, user_id, token, socket_session_id, credentials, origin,company_id=None):
    try:
        request_data_dict = json.loads(data)
        action = request_data_dict.get("action")

        # Update session with socket session IDs
        
        update_session_socket_ids(user_id, socket_session_id, app_name)

        if action in ["thumbs_up", "thumbs_down", "clear_feedback"]:
            # Try to get company_id from request_data_dict first, fallback to profile company_id
            request_company_id = request_data_dict.get("company_id")
            if request_company_id is None:
                request_company_id = company_id
            company_id_str = str(request_company_id) if request_company_id is not None else None
            await handle_thumbs_up_down_actions(action, request_data_dict, user_id, websocket, app_name, origin, company_id_str)
            return

        if action == "get_all_notifications":
            page = int(request_data_dict.get("page", 1))
            page_size = int(request_data_dict.get("page_size", 10))
            all_notifications = await handle_fetch_all_notifications(user_id, page=page, page_size=page_size, app_name=app_name)
            await manager.broadcast_json_to_user(user_id, {
                "action": "get_all_notifications",
                "status": "success",
                "notifications": all_notifications
            }, app_name=app_name)
        
        if action == "mark_as_read":
            message_id = request_data_dict.get("message_id")
            if not message_id:
                await manager.send_json(websocket, {
                    "action": "mark_as_read",
                    "status": "failure",
                    "message": "Please provide message_id to mark as read."
                })
                return
            response = await mark_notification_as_read(message_id)
            await manager.broadcast_json_to_user(user_id, {
                    "action": "mark_as_read",
                    "status": "success",
                    "response": response
                }, app_name=app_name)
            return
        

        if action == "clear_all_notification":
            response = await clear_all_notification(app_name=app_name)
            await manager.broadcast_json_to_user(user_id, {
                    "action": "clear_all_notification",
                    "response": response,
                }, app_name=app_name)
            return
        
        if action == "mark_as_read_all":
            unread_notification = await mark_all_notifications_as_read(app_name=app_name)
            await manager.broadcast_json_to_user(user_id, {
                    "status": "success",
                    "action": "mark_as_read_all",
                    "response": unread_notification,
                }, app_name=app_name)
            return

        if action == "remove_conversation_history_from_event":
            chat_session_id = request_data_dict.get("chat_session_id")
            event_id = request_data_dict.get("event_id")

            if not all([user_id, event_id]):
                await manager.send_json(websocket, {
                    "action": "remove_conversation_history_from_event",
                    "status": "error",
                    "message": "user_id and event_id are required."
                })
                return

            result = await remove_conversation_included_from_event(chat_session_id, user_id, event_id, app_name)
            await manager.send_json(websocket, result)
            return
        
        if action == "delete_session":
            chat_session_id_to_delete = request_data_dict.get("chat_session_id")
            if not chat_session_id_to_delete or not user_id:
                await manager.send_json(websocket, {
                    "action": "delete_session",
                    "status": "error",
                    "message": "chat_session_id and user_id are required for deletion."
                })
                return

            result = await delete_session(session_id=chat_session_id_to_delete, user_id=user_id)
            response={
                "action": "delete_session",
                "status": "success",
                "chat_session_id": chat_session_id_to_delete,
                "message": "Session deleted successfully."
            }
            await manager.broadcast_json_to_user(user_id, response, app_name=app_name)

            return
        
        if action == "chat":
            chat_session_id = request_data_dict.get("chat_session_id")
            if not chat_session_id:
                raise ValueError("chat_session_id is required in the request data.")
            is_new_chat = request_data_dict.get("is_new_chat")
            image_url = request_data_dict.get("image_url", None)  
            
            request_data = {
                "query": request_data_dict.get("query"),
                "session_id": chat_session_id,
                "user_id": user_id,
                "origin": origin,
                "app_name":app_name
            }
            
            # Pass image_url to LLM agent if provided and analyze with Vision API
            vision_analysis = None
            if image_url:
                try:
                    logger.info("checking for image url")
                    request_data["image_url"] = image_url
                    response = await handle_vision_api(request_data,origin,company_id)
                    logger.info(f"response: {response}")
                    request_data["extracted_info_from_image"] = response
                    vision_analysis = response
                except Exception as e:
                    logger.error(f"Error processing image with vision API: {str(e)}", exc_info=True)
                    # Still include the image_url in request_data but without extracted info
                    request_data["image_url"] = image_url
                    error_message = f"I was unable to process the uploaded image due to an error: {str(e)}. However, I can still help you with your text query."
                    request_data["extracted_info_from_image"] = error_message
            else:
                logger.info("no image url provided")


            logger.info(f"request_data: {request_data}")
            request_data = InvokeAgentRequest(**request_data)
            try:
                response = await invoke_agent(
                    request_data=request_data,
                    credentials=credentials,
                    agent_name="IATS",
                    initiate_agent_func=initiate_iats_agent
                )
                response["action"] = "chat"
                if is_new_chat is not None:
                    response["is_new_chat"] = is_new_chat
                    
                # Include image URL in response if performed
                if image_url:
                    response["image_url"] = image_url
                    
                # Save image attachment if image_url is provided
                if image_url and response.get("status") == "success":
                    try:
                        # Get event_id from the response to use as message_id
                        event_id = response.get("response", {}).get("event_id")
                        if event_id:
                            # Get database session
                            db_gen = get_db()
                            db = next(db_gen)
                            try:
                                # Save the attachment
                                attachments = [{
                                    "s3_url": image_url,
                                    "file_name": "image_attachment",
                                    "file_type": "image",
                                    "file_size": None
                                }]
                                chat_attachments_service.save_attachments(
                                    db=db,
                                    chat_session_id=chat_session_id,
                                    message_id=event_id,
                                    user_id=user_id,
                                    attachments=attachments
                                )
                                logger.info(f"Saved image attachment for message {event_id} in session {chat_session_id}")
                            finally:
                                try:
                                    db_gen.close()
                                except Exception:
                                    pass
                    except Exception as e:
                        logger.error(f"Error saving image attachment: {e}", exc_info=True)
                        send_exception_email(e, f"Error saving image attachment: {e}")
                        response = {
                            "status": "error",
                            "type": "final_response",
                            "query": request_data_dict.get("query"),
                            "message": "Failed to save image attachment, Please contact support.",
                            "session_id": chat_session_id,
                            "action": "chat",
                        }
                        await manager.send_json(websocket, response)
                        return

                # Send successful response to all user sessions
                await manager.broadcast_json_to_user(user_id, response, app_name=app_name)
            except LLMKeyNotSetException as e:
                # Re-raise LLMKeyNotSetException without modification to preserve its context
                response = {
                    "status": "error",
                    "type": "final_response",
                    "query": request_data_dict.get("query"),
                    "message": "Agent not configured for your organization, Please contact support.",
                    "session_id": chat_session_id,
                    "action": "chat",
                }
                if is_new_chat is not None:
                    response["is_new_chat"] = is_new_chat
                logger.error(f"LLMKeyNotSetException: {e}", exc_info=True)
                send_exception_email(e, f"Error invoking IATS Agent: {e}")
                await manager.send_json(websocket, response)
            except Exception as e:
                logger.error(f"Error invoking IATS Agent: {e}", exc_info=True)
                send_exception_email(e, f"Error invoking IATS Agent: {e}")
                response = {
                    "status": "error",
                    "type": "final_response",
                    "query": request_data_dict.get("query"),
                    "message": "Internal server error, Please contact support.",
                    "session_id": chat_session_id,
                    "action": "chat",
                }
                if is_new_chat is not None:
                    response["is_new_chat"] = is_new_chat
                await manager.send_json(websocket, response)

        # Handle edit_chat action
        if action == "edit_chat":
            chat_session_id = request_data_dict.get("chat_session_id")
            if not chat_session_id:
                raise ValueError("chat_session_id is required in the request data.")
            message_id = request_data_dict.get("message_id")
            image_url = request_data_dict.get("image_url", None)
            
            logger.debug(f"session_id: {chat_session_id}, user_id: {user_id}, message_id: {message_id}")
            # Preserve current message attachments if image_url is provided (for edit with new image)
            preserve_attachments = image_url is not None
            result = await remove_conversation_included_from_event(chat_session_id, user_id, message_id, app_name, preserve_attachments)
            if result["status"] == "success":
                logger.info(f"conversation history removed for session {chat_session_id} and user {user_id} ")
            else:
                logger.error(f"failed to remove conversation history for session {chat_session_id} and user {user_id}")
                await manager.send_json(websocket, result)
            logger.debug("chat action completed")

            request_data = {
                "query": request_data_dict.get("query"),
                "session_id": chat_session_id,
                "user_id": user_id,
                "origin": request_data_dict.get("origin"),
                "app_name":app_name
            }
            
            # Handle image processing for edit_chat with vision API
            vision_analysis = None
            if image_url:
                try:
                    logger.info("checking for image url in edit_chat")
                    request_data["image_url"] = image_url
                    response_vision = await handle_vision_api(request_data,origin,company_id)
                    logger.info(f"vision response: {response_vision}")
                    request_data["extracted_info_from_image"] = response_vision
                    vision_analysis = response_vision
                except Exception as e:
                    logger.error(f"Error processing image with vision API in edit_chat: {str(e)}", exc_info=True)
                    # Still include the image_url in request_data but without extracted info
                    request_data["image_url"] = image_url
                    error_message = f"I was unable to process the uploaded image due to an error: {str(e)}. However, I can still help you with your text query."
                    request_data["extracted_info_from_image"] = error_message
            else:
                logger.info("no image url provided in edit_chat")
                
            request_data = InvokeAgentRequest(**request_data)
            try:
                response = await invoke_agent(
                    request_data=request_data,
                    credentials=credentials,
                    agent_name="IATS",
                    initiate_agent_func=initiate_iats_agent
                )
                response["action"] = "edit_chat"
                response["edited_message_id"] = message_id
                
                # Include image URL in response if performed
                if image_url:
                    response["image_url"] = image_url
                    
                # Save image attachment if image_url is provided
                if image_url and response.get("status") == "success":
                    try:
                        # Get event_id from the response to use as message_id
                        event_id = response.get("response", {}).get("event_id")
                        if event_id:
                            # Get database session
                            db_gen = get_db()
                            db = next(db_gen)
                            try:
                                # Save the attachment
                                attachments = [{
                                    "s3_url": image_url,
                                    "file_name": "image_attachment",
                                    "file_type": "image",
                                    "file_size": None
                                }]
                                chat_attachments_service.save_attachments(
                                    db=db,
                                    chat_session_id=chat_session_id,
                                    message_id=event_id,
                                    user_id=user_id,
                                    attachments=attachments
                                )
                                logger.info(f"Saved image attachment for edited message {event_id} in session {chat_session_id}")
                            finally:
                                try:
                                    db_gen.close()
                                except Exception:
                                    pass
                    except Exception as e:
                        logger.error(f"Error saving image attachment in edit_chat: {e}", exc_info=True)
                        
                await manager.broadcast_json_to_user(user_id, response, app_name=app_name)
            except LLMKeyNotSetException as e:
                # Re-raise LLMKeyNotSetException without modification to preserve its context
                response = {
                    "status": "error",
                    "type": "final_response",
                    "query": request_data_dict.get("query"),
                    "message": "Agent not configured for your organization, Please contact support.",
                    "session_id": chat_session_id,
                    "action": "edit_chat",
                    "edited_message_id": message_id,
                }
                logger.error(f"LLMKeyNotSetException: {e}", exc_info=True)
                send_exception_email(e, f"Error invoking IATS Agent: {e}")
                await manager.send_json(websocket, response)
            except Exception as e:
                logger.error(f"Error invoking IATS Agent: {e}", exc_info=True)
                send_exception_email(e, f"Error invoking IATS Agent: {e}")
                response = {
                    "status": "error",
                    "type": "final_response",
                    "query": request_data_dict.get("query"),
                    "message": "Internal server error, Please contact support.",
                    "session_id": chat_session_id,
                    "action": "edit_chat",
                    "edited_message_id": message_id,
                }
                await manager.send_json(websocket, response)

        # Handle get_all_chats action
        if action == "get_all_chats":
            page = int(request_data_dict.get("page", 1))
            limit = int(request_data_dict.get("limit", 50))

            if not user_id:
                await manager.send_json(websocket, {
                    "status": "error",
                    "message": "user_id is required to fetch chat names."
                }) 

            logger.info(f"Socket request for chat names: user_id={user_id}, page={page}, limit={limit}")

            # Calculate offset for pagination
            offset = (page - 1) * limit

            # Obtain a database session
            db_gen = get_db()
            db = next(db_gen)
            try:
                sessions_data = {
                    "status": "success",
                        "action": "get_all_chats",
                        "data":{
                            "user_id": user_id,
                            "chats":  list_user_sessions(db, user_id, limit, offset, app_name=app_name),                                   
                        }
                }
            finally:
                try:
                    db_gen.close()
                except Exception:
                    pass

            await manager.send_json(websocket, sessions_data)
        
        # Handle get_chats_details action
        if action == "get_chats_details":
            chat_session_id = request_data_dict.get("chat_session_id")
            if not chat_session_id:
                raise ValueError("chat_session_id is required in the request data.")
            page = int(request_data_dict.get("page", 1))
            limit = int(request_data_dict.get("limit", 50))

            if not user_id or not chat_session_id:
                await manager.send_json(websocket, {
                    "status": "error",
                    "message": "user_id and session_id are required to fetch chat details."
                })

            logger.info(f"Socket request for chat details: user_id={user_id}, session_id={chat_session_id}, page={page}, limit={limit}")
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

            finally:
                try:
                    db_gen.close()
                except Exception:
                    pass
            message={
                "status": "success",
                "action": "get_chats_details",
                "data":{
                    "user_id": user_id,
                    "chats_details": history_details
                }
            }
            await manager.send_json(websocket, message)

        # Handle search_chat_history action
        if action == "search_chat_history":
            query = request_data_dict.get("query")
            page = int(request_data_dict.get("page", 1))
            limit = int(request_data_dict.get("limit", 50))

            if not user_id or not query:
                await manager.send_json(websocket, {
                    "status": "error",
                    "message": "user_id and query are required to search chat history."
                })

            logger.info(f"Socket request for chat search: user_id={user_id}, query={query}, page={page}, limit={limit}")

            # Calculate offset for pagination
            offset = (page - 1) * limit

            # Obtain a database session
            db_gen = get_db()
            db = next(db_gen)
            try:
                search_results = search_chat_history(db, user_id, query, limit, offset, app_name=app_name)
            finally:
                try:
                    db_gen.close()
                except Exception:
                    pass
            message={
                "status": "success",
                "action": "search_chat_history",
                "data":{
                    "user_id": user_id,
                    "search_results": search_results
                }
            }
            await manager.send_json(websocket, message)
            
        # Handle rename_chat action
        if action == "rename_chat":
            chat_session_id = request_data_dict.get("chat_session_id")
            if not chat_session_id:
                raise ValueError("chat_session_id is required in the request data.")
            new_chat_name = request_data_dict.get("new_chat_name")

            if not user_id or not chat_session_id or not new_chat_name:
                await manager.broadcast_json_to_user(user_id, {
                    "status": "error",
                    "message": "user_id, session_id, and chat_name are required to rename chat."
                }, app_name=app_name)                

            logger.info(f"Socket request for chat rename: user_id={user_id}, session_id={chat_session_id}, new_chat_name={new_chat_name}")

            # Obtain a database session
            db_gen = get_db()
            db = next(db_gen)
            try:
                rename_result = rename_chatname(db, user_id, chat_session_id, new_chat_name, app_name=app_name)
            except Exception as e:
                logger.error(f"Error renaming chat: {e}")
                rename_result = {
                    "status": "error",
                    "message": f"Failed to rename chat: {str(e)}"
                }
            finally:
                try:
                    db_gen.close()
                except Exception:
                    pass
            message={
                "status": "success",
                "action": "rename_chat",
                "data":{
                    "user_id": user_id,
                    "rename_result": rename_result
                }
            }
            await manager.broadcast_json_to_user(user_id, message, app_name=app_name)
            


    except ValueError as ve:
        logger.error(f"Invalid request data: {ve}")
        message={
            "action":action,
            "status": "error",
            "message": f"Invalid request format: {str(ve)}"
        }
        if chat_session_id:
            message["chat_session_id"]=chat_session_id
        await manager.send_json(websocket, message)
    except Exception as e:
        logger.error(f"Error processing WebSocket request: {e}", exc_info=True)
        message={
            "action":action,
            "status": "error",
            "message": f"Invalid request format: {str(e)}"
        }
        if chat_session_id:
            message["chat_session_id"]=chat_session_id
        await manager.send_json(websocket, message)
        


async def iats_websocket_handler(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if token and token.startswith("Bearer "):
        token = token[len("Bearer ") :]

    origin = websocket.headers.get("origin") 
    logger.debug(f"origin: {origin}")
    if origin and not origin.endswith("/"):
        origin += "/"
    
    socket_session_id = websocket.query_params.get("socket_session_id")

    if not socket_session_id or socket_session_id in ("null", "None"):
        logger.debug("Invalid or missing socket_session_id")
        return {"status": "error", "message": "socket_session_id is required"}
    try:
        profile_info = await get_current_profile(token, origin)
        if not profile_info or "error" in profile_info:
            logger.error(f"Failed to fetch profile info: {profile_info.get('error') if profile_info else 'No profile info returned'}")
            return {"status": "error", "message": "Authentication failed. Invalid token or user not found."}
    except Exception as e:
        logger.error(f"Exception while fetching profile info: {e}", exc_info=True)
        return {"status": "error", "message": "Access denied. Unable to fetch user profile."}
    user_id = profile_info.get("email") # user_id = {socket_ids = ["socket_1", "socket_2"]}
    company_id = profile_info.get("company_id")
    if not company_id:
        logger.error(f"Company ID not found in profile info: {profile_info}")
        return {"status": "error", "message": "company_id not found in profile info."}
    
    await manager.connect(websocket, socket_session_id)

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    heartbeat_task = asyncio.create_task(manager.heartbeat(websocket))
    update_session_socket_ids(user_id, socket_session_id, app_name)
    
    # Log WebSocket connection for network activity monitoring
    await log_websocket_connection(
        websocket=websocket,
        endpoint="/ws/invoke-iats-agent",
        user_id=user_id,
        session_id=socket_session_id,
        company_id=str(company_id) if company_id else None,
    )
    
    logger.info(f"WebSocket connection established and session updated for user: {user_id}")
    
    try:
        while True:
            data = await manager.receive_text(websocket)
            if data == "__pong__":
                logger.debug("Received pong from client.")
                continue
            logger.info(f"Received WebSocket message: {data}")
            asyncio.create_task(process_ws_message(data, websocket, user_id, token, socket_session_id, credentials, origin,company_id))
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        await manager.send_json(websocket, {
            "status": "error",
            "message": f"WebSocket error: {str(e)}"
        })
        await websocket.close()
    finally:
        heartbeat_task.cancel()
        logger.info(f"user_id {user_id} : {socket_session_id} ")
        manager.disconnect(websocket,user_id,socket_session_id,app_name)
        # Optionally, clean up session data on disconnect
        # delete_session_data(chat_session_id)
        logger.info(f"WebSocket connection terminated for socket_session_id: {socket_session_id}")