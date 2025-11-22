from datetime import datetime
import time
from typing import Any, Dict, Optional
from fastapi.responses import JSONResponse
from fastapi import HTTPException
from app.services.redis_common_state import get_session_data, save_session_data
from app.services.email_notifier import send_exception_email
from app.services.lifecycle_hooks import after_agent_invocation_callback_context, before_agent_invocation_callback_context
from app.services.my_sql_client import create_db_url
from app.services.my_sql_client import get_db
from app.models.db_models import SessionMode
from app.services.profile_block import get_my_profile_block
from app.services.state_session_manager import check_existing_session, create_user_session, update_user_session_history
from app.utils.final_logger import get_final_agent_response
from app.utils.logger import logger
from app.utils.response_formatter import format_response_for_mode
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.genai import types
from app.services.llm_engine import get_llm_engine
from app.helpers.hrms_agent import initiate_hrms_agent
from app.helpers.pm_board_story_agent import initiate_story_agent
from app.helpers.calling_agent import initiate_calling_agent
from app.helpers.pms_agent import initiate_pms_agent
import uuid
from app.services.agent_prompt_service import agent_prompt_service
from app.services.current_user_info import get_current_profile
import json
import os
from google.adk.sessions import DatabaseSessionService
from pm_board_data.core.config import KIVO_API_BASE_URL
from google.adk.agents.callback_context import CallbackContext
from app.services.lifecycle_hooks import save_data_in_triage_context
from google.adk.events import Event, EventActions
from fastapi import HTTPException
from google.adk.models.llm_response import LlmResponse
from app.services.edit_conversation import delete_session
from app.services.redis_common_state import delete_session_data
from app.services.agent_registry import AgentRegistryService
from app.helpers.BaseAgent import Kivo_LLMAgent
from app.tools.fetch_image_on_intent import push_image_s3_url
from app.utils.prompt import WHATSAPP_BUTTON_FORMATTER_PROMPT


async def initialize_default_job_state(
    app_name: str,
    user_id: str,
    session_id: str,
    session_service: DatabaseSessionService,
    session: Optional[Any] = None,
    profile_info: Dict = None,
    origin: str = None
) -> Dict[str, str]:
    try:
        if not session:
            logger.warning(f"Session not found for user_id: {user_id}, session_id: {session_id}")
            return {"status": "error", "message": "Session not found"}

        logger.debug(f"Initializing default job state for session_id: {session_id}")
        print("profile:",profile_info)
        
        # Default state with empty placeholders
        state_delta = {
            "session_id": session_id, # Origin url the website from where the user is initiating the custom matching job
            "user_id": user_id,
            "company_id": profile_info['company_id'],
            "origin": origin,
            "close_match": "",
            "profile_list": "",
            "employee_id": "",
            "app_name": app_name
        }

        # Create event with state delta
        event = Event(
            invocation_id=f"init_default_job_state_{session_id}",
            author="system",
            timestamp=time.time(),
            actions=EventActions(state_delta=state_delta)
        )
        logger.debug(f"Current state retrieved: {state_delta}")

        await session_service.append_event(session, event)
        logger.debug(f"Appended event with state_delta: {state_delta} for session_id: {session_id}")

        return {"status": "success", "message": "Job state updated with missing keys"}

    except Exception as e:
        error_msg = f"Failed to initialize default job state: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "message": error_msg}


# async def safe_run_agents_as_tool(agent_names, profile_block, session_id, user_email, app_name, company_id, origin):
#     safe_run_agents_as_tools = []

#     for agent_name in agent_names:
#         try:
#             if agent_name == "name_suggestion_agent":
#                 name_suggestion_agent = await initiate_name_suggestion_agent(session_id, profile_block, company_id, app_name, origin)
#                 if name_suggestion_agent is None:
#                     logger.error("Name Suggestion Agent initialization failed, skipping.")
#                     continue
#                 safe_run_agents_as_tools.append(AgentTool(agent=name_suggestion_agent))
#         except Exception as e:
#             logger.error(f"Error initializing {agent_name} as tool: {e}", exc_info=True)

#     return safe_run_agents_as_tools
 
# Function to initiate the triage agent with safe to run sub-agents.
async def safe_run_agent(agent_names, profile_block, session_id, user_email, app_name, company_id, origin, query, preloaded_context, mode):
    safe_run_agents = []
    errors = []
    
    for agent_name in agent_names:
        try:
            # Prepare kwargs based on agent requirements
            kwargs = {
                "session_id": session_id,
                "company_id": company_id,
                "app_name": app_name,
                "origin": origin,
                "mode": mode
            }
            
            # Add common parameters that agents might need
            kwargs.update({
                "profile_block": profile_block,
                "preloaded_context": preloaded_context,
                "user_email": user_email
            })
            
            logger.info(f"Creating agent instance for --> {agent_name} with parameters: {kwargs}")
            # Create agent instance dynamically
            agent_instance = await AgentRegistryService.create_agent_instance(agent_name, **kwargs)
            
            if agent_instance:
                safe_run_agents.append(agent_instance)
                logger.info(f"Successfully initialized agent: {agent_name}")
            
        except Exception as e:
            logger.error(f"Error initializing {agent_name}: {str(e)}", exc_info=True)
            errors.append({"agent": agent_name, "error": str(e)})
            continue
        
    if errors:
        error_message = "\n".join(str(e) for e in errors)
        error_message = f"{error_message}\nSession ID: {session_id}\nQuery: {query}\nOrigin: {origin}\nCompany ID: {company_id}"
        send_exception_email(
            Exception(error_message),
            f"Error initializing agents in safe_run_agent:\n{error_message}",
            session_id=session_id,
            origin=origin,
            company_id=company_id
        )

    return safe_run_agents
 
 
async def initiate_triage_agent(query: str, user_id: str, session_id:str, profile_info: dict, origin: str, parent_origin: str, mode: str, token: str = None, app_name:str = None, extracted_info:str = None, preloaded_context:str = None, input_data_url:str = None):
    try:
        logger.info(f"Starting triage agent initialization with preloaded_context {preloaded_context}")
        

        profile_block, parent_origin = get_my_profile_block(profile_info, parent_origin)

        # app_name and company_id for specific key pickup.
        company_id = profile_info['company_id']

        session_data = get_session_data(session_id, app_name)
        if not session_data:
            logger.debug("Creating new session with token and empty history")
            # Normalize origin before saving
            if not origin.endswith("/"):
                origin = origin + "/"

            session_data_to_save = {
                "token": token,
                "origin": origin,
                "company_id": company_id
            }
            
            # Save user's phone number from profile_info for calling agent
            if profile_info and profile_info.get("phone_number"):
                session_data_to_save["user_phone_number"] = profile_info["phone_number"]
                logger.debug(f"Saved user phone number to session: {profile_info['phone_number']}")
            
            save_session_data(session_id, session_data_to_save, app_name)
        else:
            # Normalize origin before updating session
            if not origin.endswith("/"):
                origin = origin + "/"

            session_data["token"] = token
            session_data["origin"] = origin
            session_data["company_id"] = company_id
            
            # Save user's phone number from profile_info for calling agent
            if profile_info and profile_info.get("phone_number"):
                session_data["user_phone_number"] = profile_info["phone_number"]
                logger.debug(f"Updated user phone number in session: {profile_info['phone_number']}")

            save_session_data(session_id, session_data, app_name)

        # Ensure DB session is available for session bootstrap
        db = next(get_db())
        existing_session = check_existing_session(db, session_id, app_name, mode)
        if not existing_session:
            logger.info(f"New Db Session {session_id} for mode {mode}.")
            create_user_session(db, user_id, session_id, app_name, mode)
        else:
            logger.info(f"Db Session {session_id} already exists, skipping creation.")
            if  mode != existing_session.mode:
                logger.warning(f"Db Session {session_id} already exists with mode {existing_session.mode}")
                existing_session.mode = mode
                db.commit()
                logger.warning(f"updated mode for Db Session {session_id} to {mode}")
            else:
                logger.info(f"Db Session {session_id} already exists with different mode, skipping creation.")

        if origin is None:
            origin = KIVO_API_BASE_URL
 
        if user_id.isdigit():
            mode = "whatsapp"

        logger.info(f"Mode of client is {mode}")
 
        # Get child agents for triage_agent by company ID
        sub_agents_to_attempt = AgentRegistryService.get_child_agent_names_for_company_by_id(company_id, "triage_agent")
        logger.info(f"Using database-driven child agents for triage_agent in company ID {company_id}: {sub_agents_to_attempt}")
        
        if not sub_agents_to_attempt:
            logger.warning(f"No child agents configured for triage_agent in company ID {company_id}")
            # Return professional authorization message instead of error
            unauthorized_message = "You are not authorized to access this agent. Please contact your administrator for access."
            formatted_message = format_response_for_mode(unauthorized_message, mode)
            return formatted_message, None, None

        safe_run_agents = await safe_run_agent(sub_agents_to_attempt, profile_block=profile_block, session_id=session_id, user_email=user_email, app_name=app_name, company_id=company_id, origin=origin, query=query, preloaded_context=preloaded_context, mode=mode)
        # safe_run_agents_as_tool_list = await safe_run_agents_as_tool(sub_agents_to_attempt, profile_block, session_id, user_email, app_name, company_id, origin)

        if safe_run_agents:
            for agent in safe_run_agents:
                logger.debug(f"Sub-agent initialized: {agent.name}")
        else:
            logger.warning("No sub-agents initialized or authorized for this user.")

        logger.debug(f"profile {profile_info['company_id']}")

        model = get_llm_engine(agent_name='triage_agent', company_id=company_id)

        logger.debug("LLM engine loaded successfully.")
 
        # Get dynamic instructions for triage agent based on available agents
        triage_agent_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="triage_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=profile_block,
            preloaded_context=preloaded_context
        )

        triage_agent_instructions = triage_agent_instructions + "\n" + WHATSAPP_BUTTON_FORMATTER_PROMPT
        
        date= datetime.today().strftime("%Y-%m-%d %H:%M:%S %A")
        invocation_id = None 
        async def load_triage_context(callback_context: CallbackContext):            
            logger.info(f"Loading triage context: {date}, {session_id}, {profile_block}")
            return await save_data_in_triage_context(date, session_id, profile_block, callback_context, preloaded_context)
       
        logger.info(f"Triage agent instructions ----------------------------------------------------------: {triage_agent_instructions}")

        agent = Kivo_LLMAgent(
            name=app_name,
            model=model,
            instruction=triage_agent_instructions ,
            description=agent_prompt_service.get_agent_description("triage_agent", company_id),
            sub_agents=safe_run_agents,
            before_agent_callback=load_triage_context,
            after_agent_callback=after_agent_invocation_callback_context
        )
 
        logger.info(f"Triage Agent initialized with query: {query} and query_id: {user_id}")        
        
        logger.debug(f"Generated user_id: {user_id} and session_id: {session_id}.")
 
        # Ensure session exists or create a new one for this user.
        verified_db_url=create_db_url()
        if not verified_db_url:
            logger.error("Database URL is not configured properly.")
            raise HTTPException( status_code=500, detail=f"Database URL is not configured properly." )
 
        session_service = DatabaseSessionService(db_url=verified_db_url)
        session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
        if session:
            logger.info(f"Session already exists for ID: {session_id}, reusing it.")
            
            # Check if required fields are in session state, if not save them
            current_state = session.state
            logger.debug(f"Session state raw type: {type(session.state)} value: {session.state}")
            state_delta = {}
            state_delta["current_date"] = date
            if "session_id" not in current_state:
                state_delta["session_id"] = session_id
                logger.debug(f"Adding missing session_id to existing session: {session_id}")
            
            if "user_id" not in current_state:
                state_delta["user_id"] = user_id
                logger.debug(f"Adding missing user_id to existing session: {user_id}")

            if "app_name" not in current_state and app_name:
                state_delta["app_name"] = app_name
                logger.debug(f"Adding missing app_name to existing session: {app_name}")
            
            if "company_id" not in current_state and profile_info and 'company_id' in profile_info:
                state_delta["company_id"] = profile_info['company_id']
                logger.debug(f"Adding missing company_id to existing session: {profile_info['company_id']}")
            
            if "origin" not in current_state and origin:
                state_delta["origin"] = origin
                logger.debug(f"Adding missing origin to existing session: {origin}")

            if "close_match" not in current_state:
                state_delta["close_match"] = ""
                logger.debug(f"Adding missing close_match to existing session")

            if "employee_id" not in current_state:
                state_delta["employee_id"] = ""
                logger.debug(f"Adding missing employee_id to existing session")

            if "profile_list" not in current_state:
                state_delta["profile_list"] = ""
                logger.debug(f"Adding missing profile_list to existing session")


            # If we have missing fields, save them to session state
            if state_delta:
                event = Event(
                    invocation_id=f"update_session_state_{session_id}",
                    author="system",
                    timestamp=time.time(),
                    actions=EventActions(state_delta=state_delta)
                )
                await session_service.append_event(session, event)
                logger.info(f"Updated existing session with missing fields: {list(state_delta.keys())}")
            else:
                logger.debug("No missing fields to update in session state.")
        else:
            session = await session_service.create_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id
            )
            logger.info("Session created successfully.")

            # Save mode for this session
            try:
                new_entry = SessionMode(session_id=session_id, mode=mode)
                db.add(new_entry)
                db.commit()
                logger.info(f"Mode '{mode}' saved for session_id '{session_id}' in session_modes table.")
            except Exception as db_err:
                logger.error(f"Failed to save mode for session_id '{session_id}': {db_err}", exc_info=True)
            await initialize_default_job_state(app_name, user_id, session_id, session_service, session, profile_info, origin)

        # Set is_image_upload state based on extracted_info
        if extracted_info:
            logger.info("Setting is_image_upload state to True due to extracted_info presence")
            image_upload_event = Event(
                invocation_id=f"set_image_upload_state_{session_id}",
                author="system",
                timestamp=time.time(),
                actions=EventActions(state_delta={"is_image_upload": True})
            )
            await session_service.append_event(session, image_upload_event)
        else:
            logger.info("Setting is_image_upload state to False - no extracted_info")
            image_upload_event = Event(
                invocation_id=f"set_image_upload_state_{session_id}",
                author="system", 
                timestamp=time.time(),
                actions=EventActions(state_delta={"is_image_upload": False})
            )
            await session_service.append_event(session, image_upload_event)

        # Prepare query content with extracted info if provided
        new_query = query
        if extracted_info:
            push_image_s3_url(session_id, app_name, input_data_url)
            logger.debug(f"Adding extracted_information_from_image to triage query")
            new_query = f"This content was extracted from the uploaded image: {extracted_info} and this is the user's query: {query}"
        
        # Create content from user query
        content = types.Content(role='user', parts=[types.Part(text=new_query)])
 
        # Initialize Runner with agent and session service
        runner = Runner(agent=agent, app_name="triage_agent", session_service=session_service)
        logger.info("Runner initialized. Starting agent execution.")

        # Retry logic for tool call errors
        max_retries = 1  # Only retry once to avoid infinite loops
        current_session_id = session_id
        current_runner = runner
        
        for attempt in range(max_retries + 1):
            try:
                final_response, first_message_event_id, invocation_id = await get_final_agent_response(current_runner, user_id, current_session_id, content)
                
                # Check if we got the special error code indicating tool call issues
                if final_response == "TOOL_CALL_ERROR_RETRY_NEEDED":
                    if attempt < max_retries:
                        logger.warning(f"Tool call error detected on attempt {attempt + 1}. Cleaning up session {current_session_id} and retrying...")
                        
                        # Clean up the corrupted session
                        cleanup_result = await delete_session(current_session_id, user_id, app_name)
                        logger.info(f"Session cleanup result: {cleanup_result}")
                        
                        # Also clear Redis session data
                        delete_session_data(current_session_id, app_name)
                        logger.info(f"Redis session data cleared for session {current_session_id}")
                        
                        # Generate a new session ID for retry
                        new_session_id = f"session_{user_id}_retry_{int(time.time())}"
                        logger.info(f"Generated new session ID for retry: {new_session_id}")
                        
                        # Create new session data in Redis
                        save_session_data(new_session_id, {"token": token, "origin": origin, "company_id": company_id}, app_name)
                        
                        # Create new DB session
                        create_user_session(db, user_id, new_session_id, app_name)
                        
                        # Create new ADK session
                        new_session = await session_service.create_session(
                            app_name=app_name,
                            user_id=user_id,
                            session_id=new_session_id
                        )
                        logger.info(f"New session created for retry: {new_session_id}")
                        
                        # Initialize default job state for new session
                        await initialize_default_job_state(app_name, user_id, new_session_id, session_service, new_session, profile_info, origin)
                        
                        # Create new runner with fresh session
                        current_runner = Runner(agent=agent, app_name="triage_agent", session_service=session_service)
                        current_session_id = new_session_id
                        
                        logger.info(f"Retrying with new session {new_session_id} (attempt {attempt + 2})")
                        continue
                    else:
                        logger.error(f"Max retries ({max_retries}) exceeded for tool call error. Returning error response.")
                        final_response = "I apologize, but I'm experiencing technical difficulties. Please try your request again."
                        first_message_event_id = None
                        break
                else:
                    # Success or different error - break out of retry loop
                    break
                    
            except Exception as retry_error:
                logger.error(f"Error during retry attempt {attempt + 1}: {retry_error}", exc_info=True)
                if attempt >= max_retries:
                    final_response = "I apologize, but I'm experiencing technical difficulties. Please try your request again."
                    first_message_event_id = None
                    break
                # Continue to next retry attempt
                continue

        # Format final response for the client mode
        if final_response:
            final_response = format_response_for_mode(final_response, mode)

        # Update user session history with the final session ID used
        if final_response != "TOOL_CALL_ERROR_RETRY_NEEDED" and first_message_event_id:
            await update_user_session_history(
                db,
                session_id=current_session_id,
                user_query=query,
                assistant_reply=final_response,
                event_id=first_message_event_id,
                origin=origin,
                company_id=company_id,
                app_name=app_name
            )

        return final_response, first_message_event_id, invocation_id
    
                
    except Exception as e:
        logger.error(f"Error running triage agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Triage Agent failed to process the request: {str(e)}")
    finally:
        logger.info("Triage agent execution completed.")
