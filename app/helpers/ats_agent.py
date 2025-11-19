from app.services.iats_lifecycle_hooks import after_agent_invocation_callback_context, before_agent_invocation_callback_context, simple_after_tool_modifier, simple_before_tool_modifier
from app.services.mcp_connection import connect_to_mcp_server
from app.utils.logger import logger
from google.adk.agents.llm_agent import LlmAgent
from app.services.llm_engine import get_llm_engine
from app.utils.prompt import KIVO_ATS_AGENT_PROMPT  # Updated prompt import
from app.core.constants import ATS_MCP_SERVER_URL
from datetime import datetime

async def initiate_ats_agent(company_id, app_name, origin):  # Renamed function to reflect ATS agent
    try:
        logger.debug("Initiating ATS MCP tool connection ...")
        ats_toolset = await connect_to_mcp_server(ATS_MCP_SERVER_URL)
        if not ats_toolset:
            logger.error("Failed to connect to MCP server or no tools available.")
            return None
        logger.info("Setting up ats_agent")
        ats_agent_model = get_llm_engine('ats_agent', company_id)
        date= datetime.today().strftime("%Y-%m-%d %H:%M:%S")

        ats_agent = LlmAgent(
            name="ats_agent",
            model=ats_agent_model,
            instruction=KIVO_ATS_AGENT_PROMPT.format(current_date=date),  # Updated instruction
            description="Handles queries about applicant tracking (e.g., applicants by date/source/job, interview details, job profile names).",
            output_key="ats_output",
            tools=[ats_toolset],
            before_agent_callback=before_agent_invocation_callback_context, # check before executing agent
            after_agent_callback=after_agent_invocation_callback_context ,   # check after executing agent,
            before_tool_callback=simple_before_tool_modifier,
            after_tool_callback=simple_after_tool_modifier # Assign the callback

        )
        return ats_agent  # Return the agent here

    except Exception as e:
        logger.error(f"Error in initiate_ats_agent: {e}", exc_info=True)
        return None
    
    finally:
        if ats_toolset:
            try:
                await ats_toolset.close()
            except Exception as e:
                logger.warning(f"Toolset close error: {e}", exc_info=True)