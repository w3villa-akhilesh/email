import asyncio
import json
import os
from typing import Dict, Any

from fastapi import WebSocket
from fastapi.security import HTTPAuthorizationCredentials

from app.helpers.triage import initiate_triage_agent
from app.helpers.user_agent import user_agent
from app.models.schema import TriageResponse
from app.services.current_user_info import get_current_profile
from app.services.chat_attachments import chat_attachments_service
from app.services.vision_service import handle_vision_api
from app.services.my_sql_client import get_db
from app.socket.connect import manager
from app.socket.websocket_utils import (
    handle_notification_actions,
    handle_session_management_actions,
    handle_conversation_actions,
    update_session_socket_ids,
    handle_thumbs_up_down_actions,
)
from app.services.edit_conversation import remove_conversation_included_from_event
from app.utils.logger import logger
from app.services.websocket_network_logger import log_websocket_connection

# Application name for the workplace agent



async def handle_chat_actions(
    action: str,
    request_data_dict: Dict[str, Any],
    user_id: str,
    websocket: WebSocket,
    profile_info: Dict[str, Any],
    origin: str,
    token:str,
    app_name: str,
    company_id: str = None, 
    preloaded_context: str = None
) -> None:
    """
    Handle chat-related WebSocket actions.
    
    Args:
        action: The chat action to perform
        request_data_dict: The request data dictionary
        user_id: The user ID
        websocket: The WebSocket connection object
        profile_info: The user's profile information
        origin: The origin domain
        app_name: The application name
    """
    logger.info(f"Processing chat action '{action}' for user {user_id} with preloaded_context {preloaded_context}")
    
    if action == "chat":
        logger.info("chat action is invoked")
        chat_session_id = request_data_dict.get("chat_session_id")
        if not chat_session_id:
            raise ValueError("chat_session_id is required in the request data.")
        
        is_new_chat = request_data_dict.get("is_new_chat")
        query = request_data_dict.get("query")
        session_id = chat_session_id
        parent_origin = request_data_dict.get("parent_origin", "https://demo-pms.kivo.ai/")
        mode = "web"
        image_url = request_data_dict.get("image_url", None)
        
        logger.debug(f"Processing chat query: '{query[:100]}...' for session {session_id}")
        
        # Handle image processing with vision API
        vision_analysis = None
        if image_url:
            try:
                logger.info("Processing image with vision API for workplace agent")
                vision_request_data = {
                    "query": query,
                    "session_id": session_id,
                    "user_id": user_id,
                    "origin": origin,
                    "app_name": app_name,
                    "image_url": image_url
                }
                vision_response = await handle_vision_api(vision_request_data, origin, company_id)
                logger.info(f"Vision API response: {vision_response}")
                vision_analysis = vision_response
            except Exception as e:
                logger.error(f"Error processing image with vision API: {str(e)}", exc_info=True)
                vision_analysis = f"I was unable to process the uploaded image due to an error: {str(e)}. However, I can still help you with your text query."
        else:
            logger.info("No image url provided for workplace agent")
        
        try:
            # Call triage agent directly

            if app_name == "triage_agent":
                response, event_id, invocation_id = await initiate_triage_agent(
                    query=query, 
                    user_id=user_id, 
                    session_id=session_id, 
                    profile_info=profile_info, 
                    origin=origin, 
                    parent_origin=parent_origin, 
                    mode=mode,
                    token=token,
                    app_name=app_name,
                    extracted_info=vision_analysis, 
                    preloaded_context=preloaded_context
                )
            # Call user agent directly
            elif app_name == "user_agent":
                response, event_id, invocation_id = await user_agent(
                    query, 
                    user_id=user_id, 
                    session_id=session_id, 
                    profile_info=profile_info, 
                    origin=origin, 
                    parent_origin=parent_origin, 
                    mode=mode, 
                    token=token, 
                    app_name="triage_agent"
                )

            
            # Format response for WebSocket
            ws_response = {
                "status": "success",
                "response_type": "test",
                "message": "Workplace Agent invoked",
                "full_response": response,
                "event_id": event_id,
            }
            
            if is_new_chat is not None:
                ws_response["is_new_chat"] = is_new_chat
                
            # Save image attachment if image_url is provided and response is successful
            if image_url and event_id:
                try:
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
                        logger.info(f"Saved image attachment for workplace message {event_id} in session {chat_session_id}")
                    finally:
                        try:
                            db_gen.close()
                        except Exception:
                            pass
                except Exception as e:
                    logger.error(f"Error saving image attachment for workplace agent: {e}", exc_info=True)

            formatted_response = TriageResponse(
                status="success",
                type="final_response",
                message="Workplace Agent invoked",
                query=query,
                response=ws_response,
                session_id=session_id,
                action="chat"
            )
            
            # Convert to dict and add image_url if present (matching IATS format)
            response_dict = formatted_response.model_dump()
            if image_url:
                response_dict["image_url"] = image_url
                
            await manager.broadcast_json_to_user(user_id, response_dict, app_name=app_name)
            logger.info(f"Successfully processed chat action for user {user_id}, session {session_id}")
            
        except Exception as e:
            logger.error(f"Error invoking triage agent for user {user_id}: {e}", exc_info=True)
            error_response = {
                "status": "error",
                "type": "final_response",
                "message": f"Failed to invoke Workplace Agent: {str(e)}",
                "query": query,
                "session_id": session_id,
                "action": "chat"
            }
            if is_new_chat is not None:
                error_response["is_new_chat"] = is_new_chat
            await manager.send_json(websocket, error_response)

    elif action == "edit_chat":
        chat_session_id = request_data_dict.get("chat_session_id")
        if not chat_session_id:
            raise ValueError("chat_session_id is required in the request data.")
        
        message_id = request_data_dict.get("message_id")
        image_url = request_data_dict.get("image_url", None)
        logger.debug(f"Processing edit_chat: session_id={chat_session_id}, user_id={user_id}, message_id={message_id}")
        
        # Preserve current message attachments if image_url is provided (for edit with new image)
        preserve_attachments = image_url is not None
        result = await remove_conversation_included_from_event(chat_session_id, user_id, message_id, app_name, preserve_attachments)
        if result["status"] == "success":
            logger.info(f"Conversation history removed for session {chat_session_id} and user {user_id}")
        else:
            logger.error(f"Failed to remove conversation history for session {chat_session_id} and user {user_id}")
            await manager.send_json(websocket, result)
            return
        
        logger.debug("Chat action completed, proceeding with new query")

        query = request_data_dict.get("query")
        session_id = chat_session_id
        parent_origin = request_data_dict.get("parent_origin")
        mode = "web"
        
        # Handle image processing for edit_chat with vision API
        vision_analysis = None
        if image_url:
            try:
                logger.info("Processing image with vision API for workplace edit_chat")
                vision_request_data = {
                    "query": query,
                    "session_id": session_id,
                    "user_id": user_id,
                    "origin": origin,
                    "app_name": app_name,
                    "image_url": image_url
                }
                vision_response = await handle_vision_api(vision_request_data, origin, company_id)
                logger.info(f"Vision API response for edit_chat: {vision_response}")
                vision_analysis = vision_response
            except Exception as e:
                logger.error(f"Error processing image with vision API in edit_chat: {str(e)}", exc_info=True)
                vision_analysis = f"I was unable to process the uploaded image due to an error: {str(e)}. However, I can still help you with your text query."
        else:
            logger.info("No image url provided for workplace edit_chat")
        
        try:
            # Call triage agent directly
            if app_name == "triage_agent":
               
                    response, event_id, invocation_id = await initiate_triage_agent(
                        query=query, 
                        user_id=user_id, 
                        session_id=session_id, 
                        profile_info=profile_info, 
                        origin=origin, 
                        parent_origin=parent_origin, 
                        mode=mode,
                        token=token,
                        app_name=app_name,
                        extracted_info=vision_analysis
                    )
            # Call user agent directly
            elif app_name == "user_agent":
                    response, event_id, invocation_id = await user_agent(
                        query, 
                        user_id=user_id, 
                        session_id=session_id, 
                        profile_info=profile_info, 
                        origin=origin, 
                        parent_origin=parent_origin, 
                        mode=mode, 
                        token=token, 
                        app_name=app_name
                    )

                
            # Format response for WebSocket
            ws_response = {
                "status": "success",
                "response_type": "test",
                "message": "Workplace Agent invoked",
                "full_response": response,
                "event_id": event_id,
                "edited_message_id": message_id
            }
            

                
            # Save image attachment if image_url is provided and response is successful
            if image_url and event_id:
                try:
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
                        logger.info(f"Saved image attachment for workplace edited message {event_id} in session {chat_session_id}")
                    finally:
                        try:
                            db_gen.close()
                        except Exception:
                            pass
                except Exception as e:
                    logger.error(f"Error saving image attachment in workplace edit_chat: {e}", exc_info=True)
            
            formatted_response = TriageResponse(
                status="success",
                type="final_response",
                message="Workplace Agent invoked",
                query=query,
                response=ws_response,
                session_id=session_id,
                action="edit_chat"
            )
            
            # Convert to dict and add image_url if present (matching IATS format)
            response_dict = formatted_response.model_dump()
            if image_url:
                response_dict["image_url"] = image_url
            if message_id:
                response_dict["edited_message_id"] = message_id
                
            await manager.broadcast_json_to_user(user_id, response_dict, app_name=app_name)
            logger.info(f"Successfully processed edit_chat action for user {user_id}, session {session_id}")
        
        except Exception as e:
            logger.error(f"Error invoking triage agent for edit_chat, user {user_id}: {e}", exc_info=True)
            error_response = {
                "status": "error",
                "type": "final_response",
                "message": f"Failed to invoke Workplace Agent: {str(e)}",
                "query": query,
                "session_id": session_id,
                "action": "edit_chat",
                "edited_message_id": message_id
            }
            await manager.send_json(websocket, error_response)





async def process_ws_message(
    data: str, 
    websocket: WebSocket, 
    user_id: str, 
    token: str, 
    socket_session_id: str, 
    credentials: HTTPAuthorizationCredentials, 
    origin: str, 
    profile_info: Dict[str, Any],
    app_name:str
) -> None:
    """
    Process WebSocket messages and route them to appropriate handlers.
    
    Args:
        data: The raw message data
        websocket: The WebSocket connection object
        user_id: The user ID
        token: The authentication token
        socket_session_id: The socket session ID
        credentials: The HTTP authorization credentials
        origin: The origin domain
        profile_info: The user's profile information
        app_name: app_name is based on role of employee.
    """
    try:
        request_data_dict = json.loads(data)
        action = request_data_dict.get("action")

        preloaded_context = request_data_dict.get("preloaded_context")
        
        logger.debug(f"Processing WebSocket message: action={action}, user_id={user_id} , with preloaded_context {preloaded_context}")



        # Update session with socket session IDs
        
        update_session_socket_ids(user_id, socket_session_id, app_name)

        # Handle notification actions
        if action in ["get_all_notifications", "mark_as_read", "clear_all_notification", "mark_as_read_all"]:
            await handle_notification_actions(action, request_data_dict, user_id, websocket, app_name)
            return

        # Handle conversation actions
        if action in ["remove_conversation_history_from_event", "delete_session"]:
            await handle_conversation_actions(action, request_data_dict, user_id, websocket, app_name)
            return

        # Handle chat actions
        if action in ["chat", "edit_chat"]:
            company_id = profile_info.get("company_id")
            await handle_chat_actions(action, request_data_dict, user_id, websocket, profile_info, origin, token, app_name, company_id, preloaded_context)
            return

        # Handle session management actions
        if action in ["get_all_chats", "get_chats_details", "search_chat_history", "rename_chat"]:
            await handle_session_management_actions(action, request_data_dict, user_id, websocket, app_name)
            return
        
        if action in ["thumbs_up", "thumbs_down", "clear_feedback"]:
            # Try to get company_id from request_data_dict first, fallback to profile_info
            company_id = request_data_dict.get("company_id")
            if company_id is None:
                company_id = profile_info.get("company_id")
            company_id = str(company_id) if company_id is not None else None
            await handle_thumbs_up_down_actions(action, request_data_dict, user_id, websocket, app_name, origin, company_id)
            return

        # Handle unknown actions
        logger.warning(f"Unknown action '{action}' received from user {user_id}")
        await manager.send_json(websocket, {
            "action": action,
            "status": "error",
            "message": f"Unknown action: {action}"
        })

    except ValueError as ve:
        logger.error(f"Invalid request data from user {user_id}: {ve}")
        message = {
            "action": action if 'action' in locals() else "unknown",
            "status": "error",
            "message": f"Invalid request format: {str(ve)}"
        }
        await manager.send_json(websocket, message)
    except Exception as e:
        logger.error(f"Error processing WebSocket request from user {user_id}: {e}", exc_info=True)
        message = {
            "action": action if 'action' in locals() else "unknown",
            "status": "error",
            "message": f"Error processing request: {str(e)}"
        }
        await manager.send_json(websocket, message)
        


async def workplace_websocket_handler(websocket: WebSocket) -> None:
    """
    Main WebSocket handler for the workplace agent.
    
    Args:
        websocket: The WebSocket connection object
    """
    token = websocket.query_params.get("token")
    if token and token.startswith("Bearer "):
        token = token[len("Bearer ") :]

    origin = websocket.headers.get("origin") 
    logger.info(f"WebSocket connection attempt from origin: {origin}")

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
    
    user_id = profile_info.get("email")
    is_admin = profile_info.get("is_admin", False)
    is_hr = profile_info.get("is_hr", False)

    if is_admin or is_hr:
        logger.info(f"Admin/HR user connected: {user_id}")
        app_name = "triage_agent"
    else:
        app_name = "user_agent"
        logger.info(f"WebSocket connection established for user: {user_id}, app_name: {app_name}")


    await manager.connect(websocket, socket_session_id)

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    heartbeat_task = asyncio.create_task(manager.heartbeat(websocket))
    print("socket_session_id:",socket_session_id)
    # Update session with socket session IDs
    update_session_socket_ids(user_id, socket_session_id, app_name)
    
    # Log WebSocket connection for network activity monitoring
    await log_websocket_connection(
        websocket=websocket,
        endpoint="/ws/invoke-workplace-agent",
        user_id=user_id,
        session_id=socket_session_id,
        company_id=str(profile_info.get("company_id")) if profile_info.get("company_id") else None,
    )
    
    logger.info(f"WebSocket connection established and session updated for user: {user_id}")
    
    try:
        while True:
            data = await manager.receive_text(websocket)
            if data == "__pong__":
                logger.debug(f"Received pong from user {user_id}")
                continue
            
            logger.info(f"Received WebSocket message from user {user_id}: {data[:200]}...")
            asyncio.create_task(process_ws_message(data, websocket, user_id, token, socket_session_id, credentials, origin, profile_info, app_name))
            
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}", exc_info=True)
        await manager.send_json(websocket, {
            "status": "error",
            "message": f"WebSocket error: {str(e)}"
        })
        await websocket.close()
    finally:
        heartbeat_task.cancel()
        logger.info(f"WebSocket connection terminated for user {user_id}, socket_session_id: {socket_session_id}")
        manager.disconnect(websocket, user_id, socket_session_id,app_name)