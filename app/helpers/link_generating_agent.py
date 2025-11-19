from app.services.current_user_info import get_current_profile
from app.services.lifecycle_hooks import before_agent_invocation_callback_context, after_agent_invocation_callback_context, simple_after_tool_modifier, simple_before_tool_modifier
from app.services.mcp_connection import connect_to_mcp_server
from app.utils.logger import logger
from google.adk.agents.llm_agent import LlmAgent
from app.services.llm_engine import get_llm_engine
from app.services.agent_prompt_service import agent_prompt_service
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()

async def initiate_link_generating_agent(company_id, app_name, origin, session_id=None, profile_block=None, preloaded_context=None, mode="web"):
    try:
        # logger.debug("initiate link_generating_agent mcp tool connection ...")
        # link_generating_agent_toolset = await connect_to_mcp_server(link_generating_agent)
        # if not link_generating_agent_toolset:
        #     logger.error("Failed to connect to MCP server or no tools available.")
        #     return None
        logger.info("Setting up Link Generating Agent")
    
        link_generating_agent_model = get_llm_engine('link_generating_agent', company_id)
        
        # Get dynamic instructions for link generating agent
        link_generating_agent_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="link_generating_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=profile_block,
            preloaded_context=preloaded_context,
            mode=mode,
            origin=origin  # Pass origin as additional template variable
        )

        link_generating_agent = LlmAgent(
            name="link_generating_agent",
            model=link_generating_agent_model,
            instruction=link_generating_agent_instructions,
            description=agent_prompt_service.get_agent_description("link_generating_agent", company_id),
            output_key="final_summary",
            before_agent_callback=before_agent_invocation_callback_context, # check before executing agent
            after_agent_callback=after_agent_invocation_callback_context,    # check after executing agent
            before_tool_callback=simple_before_tool_modifier,  # Fixed: added missing parameter name
            after_tool_callback=simple_after_tool_modifier # Assign the callback
        )
        return link_generating_agent  # Return the agent here
    except Exception as e:
        logger.error(f"Error in initiate_link_generating_agent: {e}", exc_info=True)  # Fixed: corrected function name in error message
        return None