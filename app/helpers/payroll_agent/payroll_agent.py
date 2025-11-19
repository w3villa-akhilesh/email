from app.services.current_user_info import get_current_profile
from app.services.lifecycle_hooks import before_agent_invocation_callback_context, after_agent_invocation_callback_context, save_data_in_hrms_context, simple_after_tool_modifier, simple_before_tool_modifier
from app.services.mcp_connection import connect_to_mcp_server
from app.utils.logger import logger
from google.adk.agents.llm_agent import LlmAgent
from app.services.llm_engine import get_llm_engine
from datetime import datetime
from app.utils.prompt import MODE_RULES
from app.services.agent_prompt_service import agent_prompt_service
from app.core.constants import PAYROLL_MCP_SERVER_URL
from google.adk.agents.callback_context import CallbackContext
from app.models.schema import strict_generation_config
from fastapi import HTTPException

async def initiate_payroll_agent(session_id, profile_block, company_id, app_name, origin, preloaded_context, mode):
    try:
        logger.debug("initiate Payroll mcp tool connection ...")
        agent_type = ["payroll"]
        exclude_tool_type = ["travel_expense", "ats", "hrms", "attendance", "recruiting"]
        include_tool_type = []
        payroll_toolset = await connect_to_mcp_server(PAYROLL_MCP_SERVER_URL, None, agent_type, exclude_tool_type, include_tool_type, session_id)
        if not payroll_toolset:
            logger.error("Failed to connect to Payroll MCP server or no tools available.")
            raise HTTPException(status_code=500, detail=f"Failed to connect to Payroll Agent MCP server")
        
        logger.info("Setting up Payroll Agent")

        payroll_agent_model = get_llm_engine(agent_name='payroll_agent', company_id=company_id)

        date = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

        async def load_payroll_context(callback_context: CallbackContext):
            return await save_data_in_hrms_context(date, profile_block, callback_context, preloaded_context, mode)

        # Get dynamic instructions for payroll agent
        payroll_agent_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="payroll_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=profile_block,
            preloaded_context=preloaded_context,
            mode=mode
        )

        # Combine dynamic prompt with shared mode rules
        combined_instruction = f"{payroll_agent_instructions}\n\n{MODE_RULES}"

        kivo_payroll_agent = LlmAgent(
            name="payroll_agent",
            model=payroll_agent_model,
            instruction=combined_instruction,
            description=agent_prompt_service.get_agent_description("payroll_agent", company_id),
            output_key="final_summary",
            tools=payroll_toolset,
            before_agent_callback=load_payroll_context, # check before executing agent
            after_agent_callback=after_agent_invocation_callback_context,    # check after executing agent
            before_tool_callback=simple_before_tool_modifier,
            after_tool_callback=simple_after_tool_modifier # Assign the callback
            # generate_content_config=strict_generation_config
        )
        return kivo_payroll_agent  # Return the agent here
    except Exception as e:
        logger.error(f"Error in initiate_payroll_agent: {e}", exc_info=True)
        raise HTTPException( status_code=500, detail=f"payroll_agent initialization failed: {str(e)}" )
    finally:
       if payroll_toolset:
            try:
                await payroll_toolset.close()
            except Exception as e:
                logger.warning(f"Payroll Toolset close error: {e}", exc_info=True)
