from app.services.lifecycle_hooks import (
    before_agent_invocation_callback_context,
    after_agent_invocation_callback_context,
    simple_after_tool_modifier,
    simple_before_tool_modifier,
)
from app.utils.logger import logger
from app.services.llm_engine import get_llm_engine
from app.services.agent_prompt_service import agent_prompt_service
from google.adk.agents.llm_agent import LlmAgent


async def initiate_lms_agent(company_id, app_name, origin, session_id=None, profile_block=None, preloaded_context=None, mode="web"):
    try:
        logger.info("Setting up LMS Agent")

        lms_agent_model = get_llm_engine('lms_agent', company_id)
        
        # Get dynamic instructions for LMS agent
        lms_agent_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="lms_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=profile_block,
            preloaded_context=preloaded_context,
            mode=mode
        )

        lms_agent = LlmAgent(
            name="lms_agent",
            model=lms_agent_model,
            instruction=lms_agent_instructions,
            description=agent_prompt_service.get_agent_description("lms_agent", company_id),
            output_key="final_summary",
            before_agent_callback=before_agent_invocation_callback_context,
            after_agent_callback=after_agent_invocation_callback_context,
            before_tool_callback=simple_before_tool_modifier,
            after_tool_callback=simple_after_tool_modifier
        )

        return lms_agent

    except Exception as e:
        logger.error(f"Error in initiate_lms_agent: {e}", exc_info=True)
        return None
