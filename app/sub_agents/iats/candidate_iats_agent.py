from app.services.iats_lifecycle_hooks import after_agent_invocation_callback_context, simple_after_tool_modifier, simple_before_tool_modifier, after_model_response_callback, fetch_and_load_available_skills
from app.services.mcp_connection import connect_to_mcp_server
from app.utils.logger import logger
from google.adk.agents.llm_agent import LlmAgent
from app.services.llm_engine import get_llm_engine
from datetime import datetime
from app.utils.prompt import CANDIDATE_IATS_AGENT_PROMPT, IATS_GLOBAL_INSTRUCTIONS
from app.services.agent_prompt_service import agent_prompt_service
from app.core.constants import CANDIDATE_IATS_AGENT_URL
from typing import Optional, Any, Dict
import time
from app.utils.logger import logger
from google.adk.agents.callback_context import CallbackContext
from app.services.agent_registry import AgentRegistryService
from google.adk.tools.agent_tool import AgentTool


async def safe_run_child_agents(parent_agent_name, child_agent_names, origin, session_id, company_id, app_name):
    """
    Initialize child agents safely with error handling.
    
    Args:
        parent_agent_name: Name of the parent agent
        child_agent_names: List of child agent names to initialize
        origin: Origin URL
        session_id: Session ID
        company_id: Company ID
        app_name: Application name
        
    Returns:
        List of agent instances
    """
    child_agents = []
    errors = []
    
    for agent_name in child_agent_names:
        try:
            logger.info(f"Creating child agent '{agent_name}' for parent '{parent_agent_name}'")
            agent_instance = await AgentRegistryService.create_agent_instance(
                agent_name,
                origin=origin,
                session_id=session_id,
                company_id=company_id,
                app_name=app_name
            )
            
            if agent_instance:
                child_agents.append(agent_instance)
                logger.info(f"Successfully initialized child agent '{agent_name}' for '{parent_agent_name}'")
        except Exception as e:
            logger.error(f"Error initializing child agent '{agent_name}' for '{parent_agent_name}': {str(e)}", exc_info=True)
            errors.append({"agent": agent_name, "error": str(e)})
            continue
    
    if errors:
        from app.utils.error_reporter import report_agent_initialization_errors
        report_agent_initialization_errors(
            errors=errors,
            session_id=session_id,
            origin=origin,
            company_id=company_id,
            context=f"safe_run_child_agents of {parent_agent_name}"
        )
    
    return child_agents


async def initiate_candidate_iats_agent(origin, session_id, company_id, app_name):
    candidate_iats_toolset = None
    try:
        logger.debug("Initiating candidate IATS MCP tool connection...")

        candidate_iats_toolset = await connect_to_mcp_server(CANDIDATE_IATS_AGENT_URL, session_id=session_id)

        if not candidate_iats_toolset:
            error_msg = "Failed to connect to MCP server or no tools available."
            logger.error(error_msg)
            raise ConnectionError(error_msg)


        logger.info("Setting up candidate_iats Agent")

        candidate_iats_agent_model = get_llm_engine('candidate_iats_agent', company_id)
        date = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

        async def load_candidate_agent_context(callback_context: CallbackContext):
            return await fetch_and_load_available_skills(session_id, callback_context)

        # Get child agents dynamically from database
        child_agent_names = AgentRegistryService.get_child_agent_names_for_company_by_id(company_id, "candidate_iats_agent")
        logger.info(f"Using database-driven child agents for candidate_iats_agent in company ID {company_id}: {child_agent_names}")
        
        # Initialize child agents dynamically
        child_agents = []
        if child_agent_names:
            child_agents = await safe_run_child_agents(
                parent_agent_name="candidate_iats_agent",
                child_agent_names=child_agent_names,
                origin=origin,
                session_id=session_id,
                company_id=company_id,
                app_name=app_name
            )
        else:
            logger.warning(f"No child agents found for candidate_iats_agent in company ID {company_id}")

        # Get dynamic instructions for candidate IATS agent
        candidate_iats_agent_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="candidate_iats_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=None,
            preloaded_context=None,
            mode="web",
            origin=origin
        )

        candidate_iats_agent = LlmAgent(
            name="candidate_iats_agent",
            model=candidate_iats_agent_model,
            instruction=f"{IATS_GLOBAL_INSTRUCTIONS}\n{candidate_iats_agent_instructions}",
            description=agent_prompt_service.get_agent_description("candidate_iats_agent", company_id),
            output_key="candidate_info",
            tools=candidate_iats_toolset,
            sub_agents=child_agents,
            before_agent_callback=load_candidate_agent_context,
            after_agent_callback=after_agent_invocation_callback_context,
            before_tool_callback=simple_before_tool_modifier,
            after_tool_callback=simple_after_tool_modifier,
            after_model_callback=after_model_response_callback
        )

        return candidate_iats_agent

    except Exception as e:
        logger.error(f"Error in initiate_candidate_iats_agent: {e}", exc_info=False)
        raise

    finally:
        if candidate_iats_toolset:
            try:
                await candidate_iats_toolset.close()
            except Exception as e:
                logger.warning(f"Toolset close error: {e}", exc_info=True)



