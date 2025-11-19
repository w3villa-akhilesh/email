from app.services.lifecycle_hooks import (
    after_agent_invocation_callback_context,
    simple_after_tool_modifier,
    simple_before_tool_modifier,
    save_data_in_hrms_context,
)
from app.utils.logger import logger
from app.services.llm_engine import get_llm_engine
from app.services.agent_prompt_service import agent_prompt_service
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from app.models.schema import strict_generation_config
from app.sub_agents.triage.name_suggestion_agent import initiate_name_suggestion_agent
from google.adk.tools.agent_tool import AgentTool
from app.helpers.performance_evaluation_agent import inject_performance_data, run_performance_evaluation_pipeline_with_retry
from datetime import datetime
from fastapi import HTTPException
from dotenv import load_dotenv
from app.helpers.BaseAgent import Kivo_LLMAgent
load_dotenv()
from app.helpers.performance_eval.tools import set_employee_id_from_name
from app.utils.prompt import WHATSAPP_BUTTON_FORMATTER_PROMPT


async def initiate_pms_agent(session_id, profile_block, company_id, app_name, origin, preloaded_context=None, mode="web"):
    try:
        logger.info("Setting up PMS Agent")
        
        pms_agent_model = get_llm_engine('pms_agent', company_id)

        # Initialize name suggestion agent
        name_suggestion_agent = await initiate_name_suggestion_agent(session_id, profile_block, company_id, app_name, origin, preloaded_context, mode)
        name_suggestion_agent_tool = AgentTool(agent=name_suggestion_agent)

        # Performance evaluation tools
        performance_eval_tools = [inject_performance_data, run_performance_evaluation_pipeline_with_retry, set_employee_id_from_name]
        
        # Combine all tools
        all_tools = [name_suggestion_agent_tool] + performance_eval_tools

        date = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

        async def load_pms_context(callback_context: CallbackContext):
            return await save_data_in_hrms_context(date, profile_block, callback_context, "")

        # Get dynamic instructions for PMS agent
        pms_agent_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="pms_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=profile_block,
            preloaded_context=preloaded_context,
            mode=mode,
            close_match=False,  # Default value for close_match
            profile_list=[],    # Default empty profile list
            employee_id=""      # Default empty employee_id
        )

        pms_agent = LlmAgent(
            name="pms_agent",
            model=pms_agent_model,
            instruction=pms_agent_instructions + "\n\n" + WHATSAPP_BUTTON_FORMATTER_PROMPT,
            description=agent_prompt_service.get_agent_description("pms_agent", company_id),
            output_key="final_summary",
            tools=all_tools,
            before_agent_callback=load_pms_context,
            after_agent_callback=after_agent_invocation_callback_context,
            before_tool_callback=simple_before_tool_modifier,
            after_tool_callback=simple_after_tool_modifier,
            generate_content_config=strict_generation_config
        )

        return pms_agent

    except Exception as e:
        logger.error(f"Error in initiate_pms_agent: {e}", exc_info=True)
        raise HTTPException( status_code=500, detail=f"pms_agent initialization failed: {str(e)}" )
