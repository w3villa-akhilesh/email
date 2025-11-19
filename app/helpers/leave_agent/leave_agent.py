from typing import Dict, Any, Optional
from app.helpers.leave_agent.tools.apply_leave import apply_leave
from app.helpers.leave_agent.tools.collect_leave import collect_leave_details
from app.services.lifecycle_hooks import after_agent_invocation_callback_context, simple_after_tool_modifier, simple_before_tool_modifier
from app.services.mcp_connection import connect_to_mcp_server
from app.utils.logger import logger
from google.adk.agents.llm_agent import LlmAgent
from app.helpers.BaseAgent import Kivo_LLMAgent
from app.services.llm_engine import get_llm_engine
from app.services.agent_prompt_service import agent_prompt_service
from app.services.agent_registry import AgentRegistryService
from app.services.email_notifier import send_exception_email
from app.utils.memory_utils import memorize
from google.adk.tools.tool_context import ToolContext
from datetime import datetime
from app.services.redis_common_state import get_session_data
import httpx
from typing import Literal
from app.core.constants import HRMS_MCP_SERVER_URL
from google.adk.agents.callback_context import CallbackContext
from fastapi import HTTPException
from app.utils.prompt import WHATSAPP_BUTTON_FORMATTER_PROMPT

# Helper functions to reduce redundancy

async def safe_run_agent(agent_names, profile_block, session_id, user_email, app_name, company_id, origin, preloaded_context, mode):
    """Initialize multiple sub-agents safely with error handling"""
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
            
            logger.info(f"Creating leave sub-agent instance for --> {agent_name} with parameters: {kwargs}")
            # Create agent instance dynamically
            agent_instance = await AgentRegistryService.create_agent_instance(agent_name, **kwargs)
            
            if agent_instance:
                safe_run_agents.append(agent_instance)
                logger.info(f"Successfully initialized leave sub-agent: {agent_name}")
            
        except Exception as e:
            logger.error(f"Error initializing {agent_name}: {str(e)}", exc_info=True)
            errors.append({"agent": agent_name, "error": str(e)})
            continue
        
    if errors:
        error_message = "\n".join(str(e) for e in errors)
        error_message = f"{error_message}\nSession ID: {session_id}\nOrigin: {origin}\nCompany ID: {company_id}"
        send_exception_email(
            Exception(error_message),
            f"Error initializing sub-agents in leave_agent:\n{error_message}",
            session_id=session_id,
            origin=origin,
            company_id=company_id
        )

    return safe_run_agents


async def fetch_leave_details_from_api(origin_url: str, token: str) -> Dict[str, Any]:
    """
    Fetch leave details from the API.

    Args:
        origin_url (str): The base URL of the API
        token (str): The authentication token

    Returns:
        dict: Raw response data from the leave categories API
    """
    url = f"{origin_url}/api/v1/settings/leave_categories.json"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Leave categories API returned status {response.status_code}: {response.text}")
                return {
                    "success": False,
                    "error": "Unable to retrieve leave data from server."
                }
            return response.json()
    except Exception as e:
        logger.error(f"Exception occurred while fetching leave details: {e}", exc_info=True)
        return {
            "success": False,
            "error": "Connection error. try again."
        }



async def load_leave_context(app_name: str, callback_context) -> Optional[Any]:
    """
    Always fetches fresh leave details before agent execution.
    This ensures leave balance template variable {leave_balance} is always up-to-date.
    """
    
    def set_fallback_context(session_id: str = None, app_name: str = None):
        """Helper function to set fallback template variables"""
        try:
            if not session_id:
                session_id = callback_context._invocation_context.session.id
            callback_context.state["session_id"] = session_id
            callback_context.state["current_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S %A")
            callback_context.state["leave_balance"] = []
            callback_context.state["app_name"] = app_name
            logger.debug(f"Setting up app_name in fallback context: {app_name}")
        except:
            pass  # In case callback_context is not available
    
    try:
        session_id = callback_context._invocation_context.session.id
        logger.info(f"Fetching fresh leave context for session: {session_id}")
        
        # Always fetch fresh session data
        session_data = get_session_data(session_id, app_name)
        if not session_data:
            logger.warning(f"Session data not found for session: {session_id}")
            set_fallback_context(session_id, app_name)
            return None

        token = session_data.get("token")
        origin_url = session_data.get("origin")
        
        if not token or not origin_url:
            logger.warning("Missing token or origin_url in session data")
            set_fallback_context(session_id, app_name)
            return None

        # Always fetch fresh leave details from API
        data = await fetch_leave_details_from_api(origin_url, token)
        
        
        if not data.get("success"):
            logger.error(f"Failed to fetch leave details: {data.get('error')}")
            set_fallback_context(session_id, app_name)
            return None

        # Process fresh leave balance data with all required fields
        leave_balance = [
            {
                "id": leave.get("id"),
                "name": leave.get("name"),
                "balance": leave.get("balance")
            }
            for leave in data.get("data", [])
        ]
        
        # Store data in context - only use leave_balance
        callback_context.state["session_id"] = session_id
        callback_context.state["current_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S %A")
        callback_context.state["leave_balance"] = leave_balance  # Structured data for both prompt and tools 
        callback_context.state["app_name"] = app_name
        logger.debug(f"Setting up app_name in tool context: {app_name}") 
        
        logger.info(f"Fresh leave context loaded successfully for session: {session_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error loading leave context: {e}", exc_info=True)
        set_fallback_context()
        return None


async def initiate_leave_agent(session_id, profile_block, company_id, app_name, origin, preloaded_context, mode, user_email=None, exclude_tool_type=None):
    try:
        leave_toolset = None
        logger.info("Setting up leave_agent with MCP and local leave tools...")
        # Use user_leave_agent for user_agent context, otherwise leave_agent
        agent_name_for_llm = "user_leave_agent" if app_name == "user_agent" else "leave_agent"
        leave_agent_model = get_llm_engine(agent_name_for_llm, company_id, app_name=app_name, origin=origin)
        agent_type = ["leave"]
        # No exclusions, only include tools tagged with "leave"
        if not exclude_tool_type:
            exclude_tool_type = []
        include_tool_type = ["leave"]

        leave_toolset = await connect_to_mcp_server(
            HRMS_MCP_SERVER_URL,
            None,
            agent_type,
            exclude_tool_type,
            include_tool_type,
            session_id
        )

        # If leave_toolset is None, assign an empty list (do not return early)
        if leave_toolset is None:
            leave_toolset = []

        # Get child agents for leave_agent by company ID
        sub_agents_to_attempt = AgentRegistryService.get_child_agent_names_for_company_by_id(company_id, "leave_agent")
        logger.info(f"Using database-driven child agents for leave_agent in company ID {company_id}: {sub_agents_to_attempt}")
        
        # Initialize sub-agents dynamically
        safe_run_agents = []
        if sub_agents_to_attempt:
            safe_run_agents = await safe_run_agent(
                sub_agents_to_attempt, 
                profile_block=profile_block, 
                session_id=session_id, 
                user_email=user_email,
                app_name=app_name, 
                company_id=company_id, 
                origin=origin, 
                preloaded_context=preloaded_context, 
                mode=mode
            )
        
        if safe_run_agents:
            for agent in safe_run_agents:
                logger.debug(f"Leave sub-agent initialized: {agent.name}")
        else:
            logger.info("No sub-agents initialized for Leave agent.")

        # Combine MCP tools with local leave tools
        all_tools = leave_toolset + [collect_leave_details, apply_leave, memorize]

        async def set_leave_context(callback_context: CallbackContext):
            return await load_leave_context(app_name, callback_context)

        # If toolset is empty, log a warning and return None
        if not all_tools:
            logger.warning("No tools available for leave agent. Agent will not be initialized.")
            raise HTTPException( status_code=500, detail=f"No tools available for leave agent. Agent will not be initialized" )

        # Get dynamic instructions for leave agent
        leave_agent_instructions = agent_prompt_service.get_agent_prompt(
            agent_name=agent_name_for_llm,
            company_id=company_id,
            session_id=session_id,
            profile_info=profile_block,
            preloaded_context=preloaded_context,
            mode=mode
        )
        logger.info(f"Leave agent instructions: {leave_agent_instructions}")
        leave_agent = LlmAgent(
            name=agent_name_for_llm,  # Use dynamic name based on context (user_leave_agent or leave_agent)
            model=leave_agent_model,
            instruction=leave_agent_instructions + "\n\n" + WHATSAPP_BUTTON_FORMATTER_PROMPT,
            description=agent_prompt_service.get_agent_description(agent_name_for_llm, company_id),
            output_key="leave_output",
            tools=all_tools,
            sub_agents=safe_run_agents,
            before_agent_callback=set_leave_context,
            after_agent_callback=after_agent_invocation_callback_context,
            before_tool_callback=simple_before_tool_modifier,
            after_tool_callback=simple_after_tool_modifier
        )

        logger.info("Leave agent initialized successfully with MCP and local tools")
        return leave_agent

    except Exception as e:
        logger.error(f"Error in initiate_leave_agent: {e}", exc_info=True)
        raise HTTPException( status_code=500, detail=f"leave_agent initialization failed: {str(e)}" )
    
    finally:
        if leave_toolset:
            try:
                print("closing leave toolset")
                await leave_toolset.close()
            except Exception as e:
                logger.warning(f"Error while closing leave_toolset: {e}")
    