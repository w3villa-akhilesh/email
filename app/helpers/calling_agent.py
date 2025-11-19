from google.adk.agents.llm_agent import LlmAgent
from app.services.mcp_connection import connect_to_mcp_server
from app.utils.logger import logger
from app.core.constants import CALLING_MCP_SERVER_URL
from app.services.llm_engine import get_llm_engine
from fastapi import HTTPException
from app.services.lifecycle_hooks import after_agent_invocation_callback_context, before_agent_invocation_callback_context, simple_after_tool_modifier, simple_before_tool_modifier
from app.services.dynamic_prompt_factory import DynamicPromptFactory
from app.services.agent_prompt_service import agent_prompt_service
from app.utils.prompt import WHATSAPP_BUTTON_FORMATTER_PROMPT

async def initiate_calling_agent(session_id, company_id, app_name, origin, profile_block=None, preloaded_context=None, mode="web"):
    try:
        logger.info("Initializing Calling Agent")
        
        # Get LLM engine for the agent dynamically
        calling_agent_model = get_llm_engine(agent_name='calling_agent', company_id=company_id)
        
        # Connect to calling MCP server (which now handles HRMS lookup internally)
        calling_toolset = await connect_to_mcp_server(server_url=CALLING_MCP_SERVER_URL, session_id=session_id)
        logger.info(f"Calling tools are --->>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> {calling_toolset}")
        if not calling_toolset:
            logger.error("Failed to connect to calling MCP server")
            raise HTTPException(status_code=500, detail=f"Failed to connect to Calling Agent MCP server")

        # Get dynamic instructions for calling agent
        calling_agent_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="calling_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=profile_block,
            preloaded_context=preloaded_context,
            mode=mode
        )

        logger.info(f"Calling agent instructions ----------------------------------------------------------: {calling_agent_instructions}")

        calling_agent = LlmAgent(
            name="calling_agent",
            model=calling_agent_model,
            instruction=calling_agent_instructions + "\n\n" + WHATSAPP_BUTTON_FORMATTER_PROMPT,
            description=agent_prompt_service.get_agent_description("calling_agent", company_id),
            tools=calling_toolset,
            before_agent_callback=before_agent_invocation_callback_context, # check before executing agent
            after_agent_callback=after_agent_invocation_callback_context,    # check after executing agent
            before_tool_callback=simple_before_tool_modifier,
            after_tool_callback=simple_after_tool_modifier # Assign the callback
        )
        
        logger.info("Calling Agent initialized successfully with the unified calling tool.")
        return calling_agent
        
    except Exception as e:
        logger.error(f"Error initializing calling agent: {e}", exc_info=True)
        raise HTTPException( status_code=500, detail=f"calling_agent initialization failed: {str(e)}" )