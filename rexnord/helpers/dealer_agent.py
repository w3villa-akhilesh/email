from rexnord.utils.logger import setup_logger
from google.adk.agents.llm_agent import LlmAgent
# Use main app's dynamic services
from app.services.llm_engine import get_llm_engine
from app.services.agent_prompt_service import agent_prompt_service
from datetime import datetime
from google.adk.agents.callback_context import CallbackContext
from rexnord.services.lifecycle_hooks import (
    after_agent_invocation_callback_context,
    save_data_in_rexnord_context,
    simple_after_tool_modifier,
    simple_before_tool_modifier,
)
from fastapi import HTTPException
from rexnord.models.schema import ResponseFormat, json_response_config
from rexnord.services.mcp_connection import connect_to_mcp_server
from rexnord.core.constants import REXNORD_MCP_SERVER_URL


logger = setup_logger("rexnord_dealer_agent")

async def save_data_in_dealer_context(date, profile_block, callback_context: CallbackContext):
    # Reuse triage context saver to store hrms-related context (profile, date)


    return await save_data_in_rexnord_context(date, "", "", callback_context)


async def initiate_dealer_agent(session_id, profile_block, company_id, app_name, origin, mode="web", **kwargs):
    """Initialize dealer agent with dynamic LLM and prompts"""
    toolset = None
    try:
        logger.debug("Initiating Dealer MCP tool connection ...")

        agent_type = ["dealer"]
        exclude_tool_type = []
        include_tool_type = []
        
        rexnord_dealer_toolset = await connect_to_mcp_server(REXNORD_MCP_SERVER_URL, None, agent_type, exclude_tool_type, include_tool_type)
        if not rexnord_dealer_toolset:
            logger.error("Failed to connect to MCP server or no tools available.")
            raise HTTPException(status_code=500, detail=f"Failed to connect to Rexnord Agent MCP server")


        logger.info("Setting up Dealer Agent")
        # Use dynamic LLM engine with agent name
        rexnord_agent_model = get_llm_engine(agent_name='dealer_agent', company_id=company_id)

        date = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

        async def load_dealer_context(callback_context: CallbackContext):
            return await save_data_in_dealer_context(date, profile_block, callback_context)

        # Get dynamic prompt for dealer_agent
        dealer_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="dealer_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=profile_block,
            mode=mode
        )

        dealer_agent = LlmAgent(
            name="dealer_agent",
            model=rexnord_agent_model,
            instruction=dealer_instructions,
            description=agent_prompt_service.get_agent_description("dealer_agent", company_id),
            output_key="final_summary",
            output_schema=ResponseFormat,
            generate_content_config=json_response_config,
            disallow_transfer_to_parent=True,
            disallow_transfer_to_peers=True,
            tools=rexnord_dealer_toolset,
            before_agent_callback=load_dealer_context,
            after_agent_callback=after_agent_invocation_callback_context,
            before_tool_callback=simple_before_tool_modifier,
            after_tool_callback=simple_after_tool_modifier,
        )
        return dealer_agent
    except Exception as e:
        logger.error(f"Error in initiate_dealer_agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"dealer_agent initialization failed: {str(e)}")
    finally:
        if toolset:
            try:
                await toolset.close()
            except Exception as e:
                logger.warning(f"Toolset close error: {e}", exc_info=True)
