from rexnord.utils.logger import setup_logger
from google.adk.agents.llm_agent import LlmAgent
# Use main app's dynamic services
from app.services.llm_engine import get_llm_engine
from app.services.agent_prompt_service import agent_prompt_service
from datetime import datetime
from google.adk.agents.callback_context import CallbackContext
from rexnord.services.lifecycle_hooks import (
    after_agent_invocation_callback_context,
    simple_after_tool_modifier,
    simple_before_tool_modifier,
)
from fastapi import HTTPException
from rexnord.core.constants import REXNORD_MCP_SERVER_URL
from rexnord.services.mcp_connection import connect_to_mcp_server

logger = setup_logger("rexnord_product_details_agent")


def get_details_of_product_selected(session_id: str, product_name: str) -> dict:
    """
    Description:
       Tool use to pick the details of a particular selected product.

    Args:
        session_id (str): Current session identifier.
        product_name (str): product name selected by user.

    Returns:
        dict: details, specifications, suggestions of the product selected by user.
    """
    logger.info(
        f"[get_details_of_product_selected] called | session_id={session_id}, product_name={product_name}"
    )

    base = "www.example.com"

    return {
        "message": "Currently I donot have any details."
    }


async def save_data_in_product_details_context(callback_context: CallbackContext):
    # Store minimal session context for product details agent
    return

async def initiate_product_details_agent(session_id, profile_block, company_id, app_name, origin, mode="web", **kwargs):
    """Initialize product details agent with dynamic LLM and prompts"""
    toolset = None
    try:
        logger.debug("Initializing Product Details agent ...")

        agent_type = ["product"]
        exclude_tool_type = []
        include_tool_type = []

        rexnord_product_toolset = await connect_to_mcp_server(REXNORD_MCP_SERVER_URL, None, agent_type, exclude_tool_type, include_tool_type)
        if not rexnord_product_toolset:
            logger.error("Failed to connect to MCP server or no tools available.")
            raise HTTPException(status_code=500, detail=f"Failed to connect to Rexnord Agent MCP server")

        logger.info("Setting up Rexnord Product Details Agent")
        # Use dynamic LLM engine with agent name
        rexnord_agent_model = get_llm_engine(agent_name='product_details_agent', company_id=company_id)

        date = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

        async def load_product_details_context(callback_context: CallbackContext):
            return await save_data_in_product_details_context(callback_context)

        # Get dynamic prompt for product_details_agent
        product_details_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="product_details_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=profile_block,
            mode=mode,
            selected_product=""  # Will be set dynamically from parent agent
        )

        product_details_agent = LlmAgent(
            name="product_details_agent",
            model=rexnord_agent_model,
            instruction=product_details_instructions,
            description=agent_prompt_service.get_agent_description("product_details_agent", company_id),
            output_key="final_summary",
            tools=rexnord_product_toolset,
            before_agent_callback=load_product_details_context,
            after_agent_callback=after_agent_invocation_callback_context,
            before_tool_callback=simple_before_tool_modifier,
            after_tool_callback=simple_after_tool_modifier,
        )
        return product_details_agent
    except Exception as e:
        logger.error(f"Error in initiate_product_details_agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"product_details_agent initialization failed: {str(e)}")
    finally:
        if toolset:
            try:
                await toolset.close()
            except Exception as e:
                logger.warning(f"Toolset close error: {e}", exc_info=True)
