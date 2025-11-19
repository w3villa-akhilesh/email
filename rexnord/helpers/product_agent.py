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
from rexnord.models.schema import ResponseFormat, json_response_config, strict_generation_config
from google.adk.tools.agent_tool import AgentTool
from rexnord.helpers.product_details_agent import initiate_product_details_agent
from rexnord.services.mcp_connection import connect_to_mcp_server
from rexnord.core.constants import REXNORD_MCP_SERVER_URL


logger = setup_logger("rexnord_product_agent")

from google.adk.tools.tool_context import ToolContext

def memorize(key: str, value: str, tool_context: ToolContext):
    """
    Memorize pieces of information, one key-value pair at a time.

    Args:
        key: the label indexing the memory to store the value.
        value: the information to be stored.
        tool_context: The ADK tool context.

    Returns:
        A status message.
    """
    mem_dict = tool_context.state
    agent_name = tool_context.agent_name
    mem_dict[key] = value
    logger.debug(f"[MEMORIZE ]{agent_name} stored {key}: {value}")
    return {"status": f'Stored "{key}": "{value}"'} 


async def save_data_in_product_agent_context(date, profile_block, callback_context: CallbackContext):
    # Reuse triage context saver to store hrms-related context (profile, date)
    return await save_data_in_rexnord_context(date, "", "", callback_context)

async def initiate_product_agent(session_id, profile_block, company_id, app_name, origin, mode="web", **kwargs):
    """Initialize product agent with dynamic LLM and prompts"""
    toolset = None
    try:
        logger.debug("Initiating Product MCP tool connection ...")

        agent_type = ["product"]
        exclude_tool_type = []
        include_tool_type = []

        rexnord_product_toolset = await connect_to_mcp_server(REXNORD_MCP_SERVER_URL, None, agent_type, exclude_tool_type, include_tool_type)
        if not rexnord_product_toolset:
            logger.error("Failed to connect to MCP server or no tools available.")
            raise HTTPException(status_code=500, detail=f"Failed to connect to Rexnord Agent MCP server")

        logger.info("Setting up Rexnord Product Agent")
        # Use dynamic LLM engine with agent name
        rexnord_agent_model = get_llm_engine(agent_name='product_agent', company_id=company_id)

        date = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

        async def load_product_agent_context(callback_context: CallbackContext):
            return await save_data_in_product_agent_context(date, profile_block, callback_context)

        product_details_agent = await initiate_product_details_agent(session_id, profile_block, company_id, app_name, origin, mode=mode)
        product_details_agent_tool = AgentTool(agent=product_details_agent)

        all_tools = rexnord_product_toolset + [product_details_agent_tool] + [memorize]

        # Get dynamic prompt for product_agent
        product_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="product_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=profile_block,
            mode=mode,
            selected_product="",  # Will be set dynamically by memorize tool
            primary_catalogue_url=""  # Will be set dynamically in callback
        )

        product_agent = LlmAgent(
            name="product_agent",
            model=rexnord_agent_model,
            instruction=product_instructions,
            description=agent_prompt_service.get_agent_description("product_agent", company_id),
            output_key="final_summary",
            output_schema=ResponseFormat,
            disallow_transfer_to_parent=True,
            disallow_transfer_to_peers=True,
            tools=all_tools,
            generate_content_config=strict_generation_config,
            before_agent_callback=load_product_agent_context,
            after_agent_callback=after_agent_invocation_callback_context,
            before_tool_callback=simple_before_tool_modifier,
            after_tool_callback=simple_after_tool_modifier,
        )
        return product_agent
    except Exception as e:
        logger.error(f"Error in initiate_product_agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"product_agent initialization failed: {str(e)}")
    finally:
        if toolset:
            try:
                await toolset.close()
            except Exception as e:
                logger.warning(f"Toolset close error: {e}", exc_info=True)
