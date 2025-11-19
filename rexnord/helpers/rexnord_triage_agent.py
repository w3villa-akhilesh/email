from datetime import datetime
import time
from typing import Any, Dict, Optional
from fastapi import HTTPException
from rexnord.services.redis_common_state import get_session_data, save_session_data
from rexnord.services.email_notifier import send_exception_email
from rexnord.services.lifecycle_hooks import after_agent_invocation_callback_context
from rexnord.services.my_sql_client import create_db_url
from rexnord.services.my_sql_client import get_db
from app.models.db_models import SessionMode
from rexnord.services.state_session_manager import check_existing_session, create_user_session, update_user_session_history
from rexnord.utils.final_logger import get_final_agent_response
from rexnord.utils.logger import setup_logger
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.genai import types
# Use the main app's dynamic LLM engine and services
from app.services.llm_engine import get_llm_engine
from app.services.agent_registry import AgentRegistryService
from app.services.agent_prompt_service import agent_prompt_service
from google.adk.sessions import DatabaseSessionService
from google.adk.agents.callback_context import CallbackContext
from rexnord.services.lifecycle_hooks import save_data_in_rexnord_context
from google.adk.events import Event, EventActions
from rexnord.services.redis_common_state import delete_session_data
from rexnord.services.edit_conversation import delete_session
from app.helpers.BaseAgent import Kivo_LLMAgent


# Use a dedicated logger name for Rexnord
logger = setup_logger("rexnord_agent")


async def initialize_default_rexnord_state(
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

        logger.debug(f"Initializing default rexnord state for session_id: {session_id}")
        
        state_delta = {
            "session_id": session_id,
            "user_id": user_id,
            "company_id": profile_info['company_id'],
            "origin": origin,
            "close_match": "",
            "current_date": "",
            "profile_info": "",
            "is_image_upload": False,
            "selected_product": ""
        }

        event = Event(
            invocation_id=f"init_default_rexnord_state_{session_id}",
            author="system",
            timestamp=time.time(),
            actions=EventActions(state_delta=state_delta)
        )

        await session_service.append_event(session, event)

        return {"status": "success", "message": "Rexnord state initialized"}

    except Exception as e:
        error_msg = f"Failed to initialize default rexnord state: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "message": error_msg}


async def safe_run_rexnord_agent(agent_names, profile_block, session_id, user_email, app_name, company_id, origin, query, mode):
    """Dynamically initialize Rexnord sub-agents using AgentRegistryService"""
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
            
            logger.info(f"Creating Rexnord agent instance for --> {agent_name} with parameters: {kwargs}")
            # Create agent instance dynamically using AgentRegistryService
            agent_instance = await AgentRegistryService.create_agent_instance(agent_name, **kwargs)
            
            if agent_instance:
                safe_run_agents.append(agent_instance)
                logger.info(f"Successfully initialized Rexnord agent: {agent_name}")
            
        except Exception as e:
            logger.error(f"Error initializing {agent_name}: {str(e)}", exc_info=True)
            errors.append({"agent": agent_name, "error": str(e)})
            continue
        
    if errors:
        error_message = "\n".join(str(e) for e in errors)
        error_message = f"{error_message}\nSession ID: {session_id}\nQuery: {query}\nOrigin: {origin}\nCompany ID: {company_id}"
        send_exception_email(
            Exception(error_message),
            f"Error initializing agents in safe_run_rexnord_agent:\n{error_message}",
            session_id=session_id,
            origin=origin,
            company_id=company_id
        )

    return safe_run_agents


async def initiate_rexnord_agent(query: str, user_id: str, session_id: str, profile_info: dict, origin: str, parent_origin: str, mode: str, token: str = None, app_name: str = None, extracted_info: str = None):
    try:
        logger.info("Starting Rexnord agent initialization.")

        logger.debug(f"[initiate_rexnord_agent] profile_info is {profile_info}")

        profile_block = profile_info

        company_id = profile_info['company_id']

        session_data = get_session_data(session_id, app_name)
        if not session_data:
            save_session_data(session_id, {"token": token, "origin": origin, "company_id": company_id}, app_name)
        else:
            session_data["token"] = token
            session_data["origin"] = origin
            session_data["company_id"] = company_id
            save_session_data(session_id, session_data, app_name)

        db = next(get_db())

        if not check_existing_session(db, session_id, app_name, mode):
            logger.info(f"New Db Session {session_id} for mode {mode}.")
            create_user_session(db, user_id, session_id, app_name, mode)
        else:
            logger.info(f"Db Session {session_id} already exists, skipping creation.")


        if user_id.isdigit():
            mode = "whatsapp"

        logger.info(f"Mode of client is {mode}")

        # Get child agents for rexnord_triage_agent dynamically from database
        sub_agents_to_attempt = AgentRegistryService.get_child_agent_names_for_company_by_id(company_id, "rexnord_triage_agent")
        logger.info(f"Using database-driven child agents for rexnord_triage_agent in company ID {company_id}: {sub_agents_to_attempt}")
        
        if not sub_agents_to_attempt:
            logger.error(f"No Rexnord agents found for company ID {company_id}")
            raise HTTPException(status_code=404, detail=f"No Rexnord agents configured for company ID {company_id}")

        safe_run_agents = await safe_run_rexnord_agent(sub_agents_to_attempt, profile_block=profile_block, session_id=session_id, user_email="", app_name=app_name, company_id=company_id, origin=origin, query=query, mode=mode)

        if safe_run_agents:
            for agent in safe_run_agents:
                logger.debug(f"Sub-agent initialized: {agent.name}")
        else:
            logger.warning("No sub-agents initialized or authorized for this user.")

        logger.debug(f"profile {profile_info['company_id']}")

        # Use dynamic LLM engine with agent name and company_id
        model = get_llm_engine(agent_name='rexnord_triage_agent', company_id=company_id)

        logger.debug("LLM engine loaded successfully.")

        # Get dynamic instructions for rexnord_triage_agent based on available agents
        rexnord_agent_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="rexnord_triage_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=profile_block,
            mode=mode,
            primary_catalogue_url=""  # Will be set dynamically in callback
        )

        logger.info(f"Rexnord agent instructions: {rexnord_agent_instructions}")

        date = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

        async def load_rexnord_context(callback_context: CallbackContext):
            logger.info(f"Loading rexnord context: {date}, {session_id}, {profile_block}")
            return await save_data_in_rexnord_context(date, session_id, "", callback_context)

        logger.info(f"Rexnord agent instructions: {rexnord_agent_instructions}")

        agent = Kivo_LLMAgent(
            name=app_name,
            model=model,
            instruction=rexnord_agent_instructions,
            description=agent_prompt_service.get_agent_description("rexnord_triage_agent", company_id),
            sub_agents=safe_run_agents,
            before_agent_callback=load_rexnord_context,
            after_agent_callback=after_agent_invocation_callback_context
        )

        logger.info(f"Rexnord Agent initialized with query: {query} and query_id: {user_id}")

        verified_db_url = create_db_url()
        if not verified_db_url:
            logger.error("Database URL is not configured properly.")
            raise HTTPException(status_code=500, detail=f"Database URL is not configured properly.")

        session_service = DatabaseSessionService(db_url=verified_db_url)
        session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
        if session:
            logger.info(f"Session already exists for ID: {session_id}, reusing it.")

            current_state = session.state
            logger.debug(f"Session state raw type: {type(session.state)} value: {session.state}")
            state_delta = {}

            if "session_id" not in current_state:
                state_delta["session_id"] = session_id
            if "user_id" not in current_state:
                state_delta["user_id"] = user_id
            if "company_id" not in current_state and profile_info and 'company_id' in profile_info:
                state_delta["company_id"] = profile_info['company_id']
            if "origin" not in current_state and origin:
                state_delta["origin"] = origin
            if "close_match" not in current_state:
                state_delta["close_match"] = ""

            state_delta["selected_product"] = ""  # reset selected_product

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
            session = await session_service.create_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id
            )
            logger.info("Session created successfully.")

            try:
                new_entry = SessionMode(session_id=session_id, mode=mode)
                db.add(new_entry)
                db.commit()
                logger.info(f"Mode '{mode}' saved for session_id '{session_id}' in session_modes table.")
            except Exception as db_err:
                logger.error(f"Failed to save mode for session_id '{session_id}': {db_err}", exc_info=True)

            await initialize_default_rexnord_state(app_name, user_id, session_id, session_service, session, profile_info, origin)

        if extracted_info:
            try:
                event = Event(
                    invocation_id=f"set_is_image_upload_true_{session_id}",
                    author="system",
                    timestamp=time.time(),
                    actions=EventActions(state_delta={"is_image_upload": True})
                )
                await session_service.append_event(session, event)
                logger.info("Set is_image_upload state to True.")
            except Exception as state_err:
                logger.error(f"Failed to update is_image_upload state: {state_err}", exc_info=True)

        # Content to send to agent (as a user message)
        content = types.Content(
            role="user",
            parts=[
                types.Part(text=query)
            ],
        )

        runner = Runner(agent=agent, app_name="rexnord_agent", session_service=session_service)
        logger.info("Runner initialized. Starting agent execution.")

        max_retries = 1
        current_session_id = session_id
        current_runner = runner

        for attempt in range(max_retries + 1):
            try:
                final_response, first_message_event_id = await get_final_agent_response(current_runner, user_id, current_session_id, content)

                if final_response == "TOOL_CALL_ERROR_RETRY_NEEDED":
                    if attempt < max_retries:
                        logger.warning(f"Tool call error on attempt {attempt + 1}. Cleaning up session {current_session_id} and retrying...")

                        cleanup_result = await delete_session(current_session_id, user_id, app_name)
                        logger.info(f"Session cleanup result: {cleanup_result}")

                        delete_session_data(current_session_id, app_name)
                        logger.info(f"Redis session data cleared for session {current_session_id}")

                        new_session_id = f"session_{user_id}_retry_{int(time.time())}"
                        logger.info(f"Generated new session ID for retry: {new_session_id}")

                        save_session_data(new_session_id, {"token": token, "origin": origin, "company_id": company_id}, app_name)

                        create_user_session(db, user_id, new_session_id, app_name)

                        new_session = await session_service.create_session(
                            app_name=app_name,
                            user_id=user_id,
                            session_id=new_session_id
                        )

                        await initialize_default_rexnord_state(app_name, user_id, new_session_id, session_service, new_session, profile_info, origin)

                        current_runner = Runner(agent=agent, app_name="rexnord_agent", session_service=session_service)
                        current_session_id = new_session_id
                        continue
                    else:
                        logger.error(f"Max retries ({max_retries}) exceeded for tool call error. Returning error response.")
                        final_response = "I apologize, but I'm experiencing technical difficulties. Please try your request again."
                        first_message_event_id = None
                        break
                else:
                    break
            except Exception as retry_error:
                logger.error(f"Error during retry attempt {attempt + 1}: {retry_error}", exc_info=True)
                if attempt >= max_retries:
                    final_response = "I apologize, but I'm experiencing technical difficulties. Please try your request again."
                    first_message_event_id = None
                    break
                continue

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

        return final_response, first_message_event_id

    except Exception as e:
        logger.error(f"Error running Rexnord agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Rexnord Agent failed to process the request: {str(e)}")
    finally:
        logger.info("Rexnord agent execution completed.")
