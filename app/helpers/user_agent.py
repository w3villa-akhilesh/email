from datetime import datetime
import time
from typing import Dict, Optional, Any
from app.services.redis_common_state import get_session_data, save_session_data
from app.utils.error_reporter import report_agent_initialization_errors
from app.services.my_sql_client import create_db_url, get_db
from app.models.db_models import SessionMode
from app.services.profile_block import get_my_profile_block
from app.services.state_session_manager import check_existing_session, create_user_session, update_user_session_history
from app.utils.final_logger import get_final_agent_response
from app.utils.logger import logger
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.genai import types
from app.services.llm_engine import get_llm_engine
from app.services.lifecycle_hooks import save_data_in_triage_context, save_data_in_user_context
from google.adk.sessions import DatabaseSessionService
from sqlalchemy.exc import OperationalError
from google.adk.agents.callback_context import CallbackContext
from google.adk.events import Event, EventActions
from app.services.mcp_connection import connect_to_mcp_server
from app.core.constants import USER_MCP_SERVER_URL
from app.services.agent_prompt_service import agent_prompt_service
from app.helpers.leave_agent.leave_agent import initiate_leave_agent
from app.helpers.pm_board_story_agent import initiate_story_agent
from app.utils.response_formatter import format_response_for_mode
from app.helpers.BaseAgent import Kivo_LLMAgent
from fastapi import HTTPException
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
            "current_date":"",
            "profile_info":"",
            "projects":"",
            "app_name":app_name
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
    

async def safe_run_agent(agent_names, profile_block, session_id, user_email, app_name, company_id, origin, query, mode, preloaded_context=None):
    """
    Iterate over every agent_name and only pass it as sub_agent if agent has been loaded without any error.
    """
    safe_run_agents = []
    errors = []
    
    from app.services.agent_registry import AgentRegistryService
    
    # Use dynamic agent factory for new system
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
                "user_email": user_email,
                "preloaded_context": preloaded_context,
                "exclude_tool_type": ["hrms"]  # Common for user agents
            })
            
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
        report_agent_initialization_errors(
            errors=errors,
            session_id=session_id,
            origin=origin,
            company_id=company_id,
            context="safe_run_agent of user agent",
            query=query
        )

    return safe_run_agents


async def user_agent(
    query: str,
    user_id: str,
    session_id: str,
    profile_info: dict,
    origin: str,
    parent_origin: str = None,
    mode: str = "web",
    token: str = None,
    app_name: str = None,
    extracted_info:str = None,
    preloaded_context: str = None
):
    try:
        logger.info("Initializing user agent with MCP tools.")

        profile_block, _, _ = get_my_profile_block(profile_info, None)
        company_id = profile_info["company_id"]
        agent_type = ["user"]

        session_data = get_session_data(session_id, app_name)
        if not session_data:
            save_session_data(session_id, {"token": token, "origin": origin, "company_id": company_id}, app_name)
        else:
            session_data.update({"token": token, "origin": origin, "company_id": company_id})
            save_session_data(session_id, session_data, app_name)

        db = next(get_d)

        if not check_existing_session(db, session_id, app_name):
            logger.info(f"New Db Session {session_id}.")
            create_user_session(db, user_id, session_id, app_name)

        verified_db_url = create_db_url()
        if not verified_db_url:
            logger.error("Database URL is not configured properly.")
            raise HTTPException(status_code=500, detail="Database URL is not configured properly.")

        session_service = DatabaseSessionService(db_url=verified_db_url)
        try:
            session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
        except OperationalError as db_op_err:
            logger.warning(f"DB OperationalError on get_session; retrying with new engine: {db_op_err}")
            session_service = DatabaseSessionService(db_url=verified_db_url)  # new engine/connection
            session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
        if session:
            logger.info(f"Session found: {session_id}")
            current_state = session.state
            state_delta = {}
            if "session_id" not in current_state:
                state_delta["session_id"] = session_id
            if "user_id" not in current_state:
                state_delta["user_id"] = user_id
            if "company_id" not in current_state:
                state_delta["company_id"] = company_id
            if "origin" not in current_state and origin:
                state_delta["origin"] = origin
            if "profile_info" not in current_state:
                state_delta["profile_info"] = profile_info
            if "app_name" not in current_state:
                state_delta["app_name"] = app_name
            if "current_date" not in current_state:
                state_delta["current_date"] = datetime.today().strftime("%Y-%m-%d %H:%M:%S")    
            if "projects" not in current_state:
                state_delta["projects"] = ""
            

            if state_delta:
                event = Event(
                    invocation_id=f"update_session_state_{session_id}",
                    author="system",
                    timestamp=time.time(),
                    actions=EventActions(state_delta=state_delta),
                )
                await session_service.append_event(session, event)

        if not session:
            logger.warning(f"Session not found. Creating new session: {session_id}")
            try:
                session = await session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
            except OperationalError as db_op_err:
                logger.warning(f"DB OperationalError on create_session; retrying with new engine: {db_op_err}")
                session_service = DatabaseSessionService(db_url=verified_db_url)
                session = await session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
            try:
                new_entry = SessionMode(session_id=session_id, mode=mode)
                db.add(new_entry)
                db.commit()
            except Exception as db_err:
                logger.error(f"Error saving session mode: {db_err}", exc_info=True)
            await initialize_default_job_state(app_name, user_id, session_id, session_service, session, profile_info, origin)
        
        # Initialize state if missing
        
        date = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

        async def load_context(callback_context: CallbackContext):
            logger.info(f"Loading context: {date}")
            return await save_data_in_user_context(date, session_id, profile_block, callback_context, preloaded_context)

        # Connect to MCP toolset
        logger.debug("Connecting to MCP server for user tools...")
        include_tool_type = []  
        exclude_tool_type = []  
        mcp_toolset = await connect_to_mcp_server(
            USER_MCP_SERVER_URL,
            None,
            agent_type=agent_type,
            exclude_tool_type=exclude_tool_type,
            include_tool_type=include_tool_type,
            session_id = session_id
        )

        if not mcp_toolset:
            logger.warning("No MCP tools loaded; proceeding with agent-only setup.")
            tools = []
        else:
            logger.info(f"Loaded {len(mcp_toolset)} tools from MCP.")
            tools = mcp_toolset

        # Get agents dynamically from database for user agent
        from app.services.agent_registry import AgentRegistryService
        
        # Get child agents for user_agent by company ID
        sub_agents_to_attempt = AgentRegistryService.get_child_agent_names_for_company_by_id(company_id, "user_agent")
        logger.info(f"Using database-driven child agents for user_agent in company ID {company_id}: {sub_agents_to_attempt}")
        
        if not sub_agents_to_attempt:
            logger.warning(f"No child agents configured for user_agent in company ID {company_id}")
            # Return professional authorization message instead of error
            unauthorized_message = "You are not authorized to access this agent. Please contact your administrator for access."
            formatted_message = format_response_for_mode(unauthorized_message, mode)
            return formatted_message, None, None

        safe_run_agents = await safe_run_agent(sub_agents_to_attempt, profile_block=profile_block, session_id=session_id, user_email="", app_name=app_name, company_id=company_id, origin=origin, query=query, mode=mode, preloaded_context=preloaded_context)
        # safe_run_agents_as_tool_list = await safe_run_agents_as_tool(sub_agents_to_attempt, profile_block, session_id, user_email, app_name, company_id, origin)

        if safe_run_agents:
            for agent in safe_run_agents:
                logger.debug(f"Sub-agent initialized: {agent.name}")
        else:
            logger.warning("No sub-agents initialized or authorized for this user.")

        # Get dynamic instructions for user agent
        user_agent_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="user_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=profile_block,
            preloaded_context=preloaded_context or {},
            mode=mode
        )

        # Setup agent
        agent = Kivo_LLMAgent(
            name=app_name,
            model=get_llm_engine(agent_name="user_agent", company_id=company_id),
            instruction=user_agent_instructions + "\n\n" + WHATSAPP_BUTTON_FORMATTER_PROMPT,
            description=agent_prompt_service.get_agent_description("user_agent", company_id),
            sub_agents=safe_run_agents,
            tools=tools,
            before_agent_callback=load_context,
        )

        content = types.Content(role="user", parts=[types.Part(text=query)])
        runner = Runner(agent=agent, app_name=app_name, session_service=session_service)

        final_response, first_message_event_id, invocation_id = await get_final_agent_response(runner, user_id, session_id, content)

        if final_response:
            final_response = format_response_for_mode(final_response, mode)

        await update_user_session_history(
            db,
            session_id=session_id,
            user_query=query,
            assistant_reply=final_response,
            event_id=first_message_event_id,
            origin=origin,
            company_id=company_id,
            app_name=app_name,
        )

        # Close DB session explicitly to avoid leaking pooled connections
        try:
            return final_response, first_message_event_id, invocation_id
        finally:
            try:
                db.close()
            except Exception:
                pass

    except Exception as e:
        logger.error(f"Error running user agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"User Agent failed to process the request: {str(e)}")
    