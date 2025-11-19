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


logger = setup_logger("rexnord_faq_agent")


async def save_data_in_faq_context(date, profile_block, callback_context: CallbackContext):
    # Minimal session context for FAQ agent
    return await save_data_in_rexnord_context(date, "", "", callback_context)


async def initiate_faq_agent(session_id, profile_block, company_id, app_name, origin, mode="web", **kwargs):
    """Initialize FAQ agent with dynamic LLM and prompts"""
    toolset = None
    try:
        logger.debug("Initializing FAQ Agent ...")

        # Use dynamic LLM engine with agent name
        model = get_llm_engine(agent_name='faq_agent', company_id=company_id)
        date = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

        async def load_faq_context(callback_context: CallbackContext):
            return await save_data_in_faq_context(date, profile_block, callback_context)

        # Get dynamic prompt for faq_agent
        faq_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="faq_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=profile_block,
            mode=mode
        )

        faq_agent = LlmAgent(
            name="faq_agent",
            model=model,
            instruction=faq_instructions,
            description=agent_prompt_service.get_agent_description("faq_agent", company_id),
            output_key="final_summary",
            output_schema=ResponseFormat,
            generate_content_config=json_response_config,
            disallow_transfer_to_parent=True,
            disallow_transfer_to_peers=True,
            before_agent_callback=load_faq_context,
            after_agent_callback=after_agent_invocation_callback_context,
            before_tool_callback=simple_before_tool_modifier,
            after_tool_callback=simple_after_tool_modifier,
        )
        return faq_agent
    except Exception as e:
        logger.error(f"Error in initiate_faq_agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"faq_agent initialization failed: {str(e)}")
    finally:
        if toolset:
            try:
                await toolset.close()
            except Exception as e:
                logger.warning(f"Toolset close error: {e}", exc_info=True)
