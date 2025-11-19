from app.models.schema import ScoringCriteria, json_response_config
from app.services.iats_lifecycle_hooks import after_model_response_callback
from app.services.llm_engine import get_llm_engine
from app.utils.logger import logger
from google.adk.agents.llm_agent import LlmAgent
from app.utils.prompt import SCORING_CRITERIA_AGENT_PROMPT, IATS_GLOBAL_INSTRUCTIONS
from app.services.agent_prompt_service import agent_prompt_service

async def initiate_scoring_criteria_agent(origin, session_id, company_id, app_name):
    """
    Initializes and returns the scoring_criteria_agent.

    Returns:
        LlmAgent: The initialized scoring_criteria_agent.
    """
    try:
        logger.debug(f"Initiating scoring_criteria_agent...{origin}")

        scoring_criteria_model = get_llm_engine('scoring_criteria_agent', company_id)

        # Get dynamic instructions for scoring criteria agent
        scoring_criteria_agent_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="scoring_criteria_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=None,
            preloaded_context=None,
            mode="web",
            origin=origin
        )

        scoring_criteria_agent = LlmAgent(
            name="scoring_criteria_agent",
            model=scoring_criteria_model,
            instruction=f"{IATS_GLOBAL_INSTRUCTIONS}\n{scoring_criteria_agent_instructions}",
            description=agent_prompt_service.get_agent_description("scoring_criteria_agent", company_id),
            output_key="scoring_criteria",
            after_model_callback=after_model_response_callback,
        )

        return scoring_criteria_agent

    except Exception as e:
        logger.error(f"Error in initiate_scoring_criteria_agent: {e}", exc_info=True)
        raise 