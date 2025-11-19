from app.services.current_user_info import get_current_profile
from app.services.iats_lifecycle_hooks import before_agent_invocation_callback_context, after_agent_invocation_callback_context, simple_after_tool_modifier, simple_before_tool_modifier, after_model_response_callback
from app.services.mcp_connection import connect_to_mcp_server
from app.utils.logger import logger
from google.adk.agents.llm_agent import LlmAgent
from app.services.llm_engine import get_llm_engine
from datetime import datetime
from app.utils.prompt import job_profile_agent_PROMPT, IATS_GLOBAL_INSTRUCTIONS
from app.services.agent_prompt_service import agent_prompt_service
from app.core.constants import job_profile_agent_URL
from google.adk.agents.callback_context import CallbackContext
from google.adk.sessions import DatabaseSessionService
from app.services.my_sql_client import create_db_url
from google.adk.tools.tool_context import ToolContext
from app.utils.memory_utils import memorize

async def initiate_job_profile_agent(origin, session_id, company_id, app_name):
    hiring_iats_toolset = None
    try:
        logger.debug("Initiating hiring_iats MCP tool connection ...")
        hiring_iats_toolset = await connect_to_mcp_server(job_profile_agent_URL, session_id=session_id)

        if not hiring_iats_toolset:
            error_msg = "Failed to connect to MCP server or no tools available."
            logger.error(error_msg)
            raise ConnectionError(error_msg)


        logger.info("Setting up hiring_iats Agent")

        # Get actual MCP tools list
        # mcp_tools = await hiring_iats_toolset.get_tools()

        # Combine local + remote tools
        all_tools = [memorize] + hiring_iats_toolset

        job_profile_agent_model = get_llm_engine('job_profile_agent', company_id)

        # Get dynamic instructions for job profile agent
        job_profile_agent_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="job_profile_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=None,
            preloaded_context=None,
            mode="web",
            origin=origin
        )

        job_profile_agent = LlmAgent(
            name="job_profile_agent",
            model=job_profile_agent_model,
            instruction=f"{IATS_GLOBAL_INSTRUCTIONS}\n{job_profile_agent_instructions}",
            description=agent_prompt_service.get_agent_description("job_profile_agent", company_id),
            output_key="hiring_info",
            tools=all_tools,
            before_agent_callback=before_agent_invocation_callback_context,
            after_agent_callback=after_agent_invocation_callback_context,
            before_tool_callback=simple_before_tool_modifier,
            after_tool_callback=simple_after_tool_modifier,
            after_model_callback=after_model_response_callback
        )

        return job_profile_agent

    except Exception as e:
        logger.error(f"Error in initiate_job_profile_agent: {e}", exc_info=True)
        raise

    finally:
        if hiring_iats_toolset:
            try:
                await hiring_iats_toolset.close()
            except Exception as e:
                logger.warning(f"Toolset close error: {e}", exc_info=True)
