from datetime import datetime
import time
from typing import Any, Dict, Optional
from fastapi import HTTPException
from app.services.lifecycle_hooks import after_agent_invocation_callback_context
from app.services.my_sql_client import create_db_url
from app.services.my_sql_client import get_db
from app.services.state_session_manager import check_existing_session, create_user_session, update_user_session_history
from app.services.profile_block import get_my_profile_block
from app.utils.final_logger import get_final_agent_response
from app.utils.logger import logger
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.genai import types
from app.services.llm_engine import get_llm_engine
import uuid
from app.utils.history import construct_previous_context
from app.utils.prompt import CRM_TRIAGE_AGENT_PROMPT, GREETING_INSTRUCTIONS
from app.services.agent_prompt_service import agent_prompt_service
from app.models.db_models import SessionMode
import json
import os
from google.adk.sessions import DatabaseSessionService
from app.core.constants import ALLOWED_CALLING_EMAILS
from app.services.redis_common_state import get_session_data, save_session_data
from pm_board_data.core.config import KIVO_API_BASE_URL
from google.adk.agents.callback_context import CallbackContext
from app.services.lifecycle_hooks import save_data_in_crm_triage_context
from google.adk.events import Event, EventActions
from app.services.redis_common_state import delete_session_data
from app.services.edit_conversation import delete_session

# Dynamic agent loading
from app.services.agent_registry import AgentRegistryService


async def initialize_default_job_state(
    app_name: str,
    user_id: str,
    session_id: str,
    session_service: DatabaseSessionService,
    session: Optional[Any] = None,
    profile_info: Dict = None,
    origin: str = None,
    account_id: str = None
) -> Dict[str, str]:
    try:
        if not session:
            logger.warning(f"Session not found for user_id: {user_id}, session_id: {session_id}")
            return {"status": "error", "message": "Session not found"}

        logger.debug(f"Initializing default job state for session_id: {session_id}")
        print("profile:",profile_info)

        state_delta = {
            "session_id": session_id,            
            "user_id": user_id,
            "company_id": profile_info['company_id'],
            "origin": origin,
            "account_id": account_id
            }

        event = Event(
            invocation_id=f"init_default_job_state_{session_id}",
            author="system",
            timestamp=time.time(),
            actions=EventActions(state_delta=state_delta)
        )
        logger.debug(f"Current state retrieved: {state_delta}")

        await session_service.append_event(session, event)
        logger.debug(f"Appended event with state_delta: {state_delta} for session_id: {session_id}")

        return {"status": "success", "message": "Job state initialized successfully"}

    except Exception as e:
        error_msg = f"Failed to initialize default job state: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "message": error_msg}


async def safe_run_agent(agent_names, profile_block, session_id, user_email, app_name, company_id, origin, query, mode):
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
                "user_email": user_email
            })
            
            logger.info(f"Creating CRM sub-agent instance for --> {agent_name} with parameters: {kwargs}")
            # Create agent instance dynamically
            agent_instance = await AgentRegistryService.create_agent_instance(agent_name, **kwargs)
            
            if agent_instance:
                safe_run_agents.append(agent_instance)
                logger.info(f"Successfully initialized CRM sub-agent: {agent_name}")
            
        except Exception as e:
            logger.error(f"Error initializing {agent_name}: {str(e)}", exc_info=True)
            errors.append({"agent": agent_name, "error": str(e)})
            continue
    
    if errors:
        error_message = "\n".join(str(e) for e in errors)
        error_message = f"{error_message}\nSession ID: {session_id}\nQuery: {query}\nOrigin: {origin}\nCompany ID: {company_id}"
        logger.warning(f"Some CRM sub-agents failed to initialize: {error_message}")

    return safe_run_agents

# this definition is used to start the crm_triage_agent
async def initiate_crm_triage_agent(query: str, user_id: str, session_id: str, profile_info: dict, origin: str, parent_origin: str, mode: str, account_id: str, token: str, agent_id:str, app_name:str, extracted_info:str = None):
    try:
        logger.info("Starting CRM triage agent initialization.")

        logger.debug(f"App context → app_name: {app_name}, account_id: {account_id}, origin: {origin}")

        profile_block, user_email, parent_origin = get_my_profile_block(profile_info, parent_origin)

        app_name = "crm_triage_agent"
        company_id = profile_info['company_id']



        # Persist token/origin/account_id in session (merge/overwrite as needed)
        session_data = get_session_data(session_id, app_name)
        if not session_data:
            logger.warning(f"session data not found for {session_id} (first write just executed)")
            # Creating new session with token and empty history
            save_session_data(session_id, {"token": token, "origin": origin, "company_id": company_id, "account_id": account_id}, app_name)
        else:
            # Load history from session data
            session_data["token"] = token
            session_data["origin"] = origin
            session_data["company_id"] = company_id
            save_session_data(session_id, {'token': token, 'origin': origin, 'company_id': company_id, "account_id": account_id, 'agent_id': agent_id}, app_name)
        
        # Ensure DB session is available for session bootstrap
        db = next(get_db())

        if not check_existing_session(db, session_id, app_name, mode):
            logger.info(f"New Db Session {session_id} for mode {mode}.")
            create_user_session(db, user_id, session_id, app_name, mode)
        else:
            logger.info(f"Db Session {session_id} already exists, skipping creation.")

        if origin is None:
            origin = KIVO_API_BASE_URL
 
        if user_id.isdigit():
            mode = "whatsapp"

        logger.info(f"Mode of client is {mode}")

        # Get child agents for crm_triage_agent by company ID
        sub_agents_to_attempt = AgentRegistryService.get_child_agent_names_for_company_by_id(company_id, "crm_triage_agent")
        logger.info(f"Using database-driven child agents for crm_triage_agent in company ID {company_id}: {sub_agents_to_attempt}")
        
        if not sub_agents_to_attempt:
            logger.warning(f"No CRM child agents found for company ID {company_id}")
            sub_agents_to_attempt = []  # Continue with empty list

        safe_run_agents = await safe_run_agent(
            sub_agents_to_attempt,
            profile_block=profile_block,
            session_id=session_id,
            user_email=user_email,
            app_name=app_name,
            company_id=company_id,
            origin=origin,
            query=query,
            mode=mode
        )

        if not safe_run_agents:
            logger.warning("No sub-agents initialized or authorized for this user.")

        model = get_llm_engine(agent_name='crm_triage_agent', company_id=company_id)
        logger.info(f"LLM engine loaded successfully.")

        # Get dynamic instructions for CRM triage agent
        triage_agent_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="crm_triage_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=profile_block,
            preloaded_context=None,
            mode=mode
        )
        
        date = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

        async def load_triage_context(callback_context: CallbackContext):
            logger.info(f"Loading triage context: {date}, {session_id}, {profile_block}")
            return await save_data_in_crm_triage_context(date, session_id, profile_block, callback_context)

        agent = LlmAgent(
            name=app_name,
            model=model,
            instruction=triage_agent_instructions,
            description=agent_prompt_service.get_agent_description("crm_triage_agent", company_id),
            sub_agents=safe_run_agents,
            before_agent_callback=load_triage_context,
            after_agent_callback=after_agent_invocation_callback_context
        )

        verified_db_url = create_db_url()
        if not verified_db_url:
            logger.error("Database URL is not configured properly.")
            raise HTTPException( status_code=500, detail=f"Database URL is not configured properly." )

        session_service = DatabaseSessionService(db_url=verified_db_url)
        session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)

        if session:
            logger.info(f"Session already exists for ID: {session_id}, reusing it.")
            current_state = session.state
            state_delta = {}

            if "session_id" not in current_state:
                state_delta["session_id"] = session_id
                logger.debug(f"Adding missing session_id to existing session: {session_id}")

            if "user_id" not in current_state:
                state_delta["user_id"] = user_id
                logger.debug(f"Adding missing user_id to existing session: {user_id}")
            
            if "company_id" not in current_state and profile_info and 'company_id' in profile_info:
                state_delta["company_id"] = profile_info['company_id']
                logger.debug(f"Adding missing company_id to existing session: {profile_info['company_id']}")
            
            if "origin" not in current_state and origin:
                state_delta["origin"] = origin
                logger.debug(f"Adding missing origin to existing session: {origin}")

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
                db.rollback()
                logger.error(f"Failed to save mode for session_id '{session_id}': {db_err}", exc_info=True)
            await initialize_default_job_state(app_name, user_id, session_id, session_service, session, profile_info, origin, account_id)

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
            logger.debug(f"Adding extracted_information_from_image to triage query")
            new_query = f"This content was extracted from the uploaded image: {extracted_info} and this is the user's query: {query}"
        logger.debug(f"checking -------------------------- \n {new_query}")
        # Create content from user query
        content = types.Content(role='user', parts=[types.Part(text=new_query)])
        logger.debug(f"content checking {content}")
        # Initialize Runner with agent and session service
        runner = Runner(agent=agent, app_name=app_name, session_service=session_service)
        logger.info("Runner initialized. Starting CRM triage agent execution.")

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
                        logger.debug(f"the app_name -------------------------->{app_name}")
                        
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
                        await initialize_default_job_state(app_name, user_id, new_session_id, session_service, new_session, profile_info, origin, account_id)
                        
                        # Create new runner with fresh session
                        current_runner = Runner(agent=agent, app_name="crm_triage_agent", session_service=session_service)
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
        logger.debug(f"user session update hisrtory -------------------------> {final_response}")

        return final_response, first_message_event_id
    
                
    except Exception as e:
        logger.error(f"Error running triage agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Crm_Triage Agent failed to process the request: {str(e)}")
    finally:
        logger.info("Crm_Triage agent execution completed.")
