from typing import Optional, Any, Dict
from fastapi import HTTPException
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from app.services.iats_lifecycle_hooks import after_agent_invocation_callback_context, simple_after_tool_modifier, simple_before_tool_modifier, after_model_response_callback
from app.services.llm_engine import get_llm_engine
from app.utils.logger import logger
from app.utils.prompt import INTERVIEW_SCHEDULER_AGENT_PROMPT, IATS_GLOBAL_INSTRUCTIONS
from app.services.agent_prompt_service import agent_prompt_service
from app.sub_agents.iats.tools.collect_interview_details import collect_interview_details
from app.sub_agents.iats.tools.schedule_interview import schedule_interview
from app.sub_agents.iats.interview_context import load_interview_context
from app.utils.memory_utils import memorize


async def initiate_interview_scheduler_agent(origin, session_id, company_id, app_name):
    """
    Initialize and configure the interview scheduler agent for IATS.
    
    This function sets up an LLM agent specifically designed to handle interview
    scheduling workflows including collecting interview details, confirming with
    users, and scheduling interviews through various platforms.
    
    Args:
        origin (str): The origin URL of the request/application
        session_id (str): Unique identifier for the current user session
        company_id (str): Company identifier for context and configuration
        app_name (str): Application name for agent configuration
        
        
    Tools included:
        - collect_interview_details: Gather scheduling information from users
        - schedule_interview: Execute the actual interview scheduling
        - memorize: Store context and information across sessions
        
    """
    interview_scheduler_toolset = None
    try:
        logger.info("Setting up interview_scheduler Agent with local tools...")
        
        interview_scheduler_agent_model = get_llm_engine('interview_scheduler_agent', company_id)
        
        # Define local interview tools
        local_tools = [collect_interview_details, schedule_interview, memorize]
        all_tools = local_tools

        async def set_interview_context(callback_context: CallbackContext):
            return await load_interview_context(app_name, callback_context)

        # Get dynamic instructions for interview scheduler agent
        interview_scheduler_agent_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="interview_scheduler_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=None,
            preloaded_context=None,
            mode="web",
            origin=origin
        )

        interview_scheduler_agent = LlmAgent(
            name="interview_scheduler_agent",
            model=interview_scheduler_agent_model,
            instruction=f"{IATS_GLOBAL_INSTRUCTIONS}\n{interview_scheduler_agent_instructions}",
            description=agent_prompt_service.get_agent_description("interview_scheduler_agent", company_id),
            output_key="interview_scheduler_info",
            tools=all_tools,
            before_agent_callback=set_interview_context,
            after_agent_callback=after_agent_invocation_callback_context,
            before_tool_callback=simple_before_tool_modifier,
            after_tool_callback=simple_after_tool_modifier,
            after_model_callback=after_model_response_callback
        )

        logger.info("Interview scheduler agent initialized successfully")
        return interview_scheduler_agent

    except Exception as e:
        logger.error(f"Error in initiate_interview_scheduler_agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Interview scheduler agent initialization failed: {str(e)}")
    
    finally:
        if interview_scheduler_toolset:
            try:
                await interview_scheduler_toolset.close()
            except Exception as e:
                logger.warning(f"Error while closing interview_scheduler_toolset: {e}")
