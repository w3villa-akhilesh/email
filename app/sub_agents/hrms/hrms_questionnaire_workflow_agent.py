import requests
import json
from typing import Optional
from dotenv import load_dotenv
from datetime import datetime
from google.adk.agents.llm_agent import LlmAgent
from app.helpers.BaseAgent import Kivo_LLMAgent
from google.adk.agents.callback_context import CallbackContext
from app.services.llm_engine import get_llm_engine
from app.services.lifecycle_hooks import (
    after_agent_invocation_callback_context,
    save_data_in_hrms_context,
    simple_after_tool_modifier,
    simple_before_tool_modifier,
)
from app.services.redis_common_state import get_session_data
from app.utils.logger import logger
from app.services.agent_prompt_service import agent_prompt_service
from app.core.constants import KNOWLEDGE_BASE_API_KEY, KNOWLEDGE_BASE_URL


load_dotenv()


# async def get_required_workflow(url: str, title: str, session_id: str):
#     """
#     Fetch HRMS workflow details matching the user's query.

#     Args:
#     - title (str): Workflow/procedure related user query.
#     - url (str): path of the module which is related to title.
#     - session_id (str): Unique identifier to fetch session context.
#     """

#     logger.info(
#         f"[get_required_workflow] tool invoked with query={title} session_id={session_id}"
#     )
#     app_name = "triage_agent"
#     session_data = get_session_data(session_id, app_name) or {}

#     # extract company_id, origin
#     company_id = session_data.get("company_id")
#     origin = session_data.get("origin")

#     if not origin:
#         logger.warning("[get_required_workflow] origin missing in session data")

#     if not company_id:
#         logger.warning("[get_required_workflow] company_id missing in session data")

#     if not KNOWLEDGE_BASE_API_KEY:
#         logger.warning("[get_required_workflow] KNOWLEDGE_BASE_API_KEY is not set.")


#     payload = {
#         "query": title,
#         "url":url,
#         "company_id": company_id,
#         "index_name": "hrms_index",
#     }

#     headers = {
#         "Authorization": f"{KNOWLEDGE_BASE_API_KEY}",
#         "Content-Type": "application/json",
#         "X-Origin": origin
#     }

#     url = f"{KNOWLEDGE_BASE_URL}/search"

#     try:
#         # Use POST with JSON body for search queries
#         response = requests.post(url=url, json=payload, headers=headers, timeout=10)
#         response.raise_for_status()
#         hrms_info_json = response.json()
#         logger.debug(f"[get_required_workflow] fetched HRMS info: {hrms_info_json}")
#         return hrms_info_json
#     except requests.RequestException as e:
#         logger.error(f"[get_required_workflow] request error: {e}", exc_info=True)
#         return {"error": "Failed to fetch HRMS workflow", "details": str(e)}
#     except ValueError as e:
#         # JSON decoding error
#         logger.error(f"[get_required_workflow] invalid JSON response: {e}", exc_info=True)
#         return {"error": "Invalid response from HRMS service"}


async def get_required_workflow(title: str, session_id: str):
    """
    Fetch HRMS workflow details matching the user's query.

    Args:
    - title (str): Workflow/procedure related user query.
    - session_id (str): Unique identifier to fetch session context.
    """

    logger.info(
        f"[get_required_workflow] tool invoked with query={title} session_id={session_id}"
    )
    app_name = "triage_agent"
    session_data = get_session_data(session_id, app_name) or {}

    # extract company_id, origin
    company_id = session_data.get("company_id")
    origin = session_data.get("origin")

    if not origin:
        logger.warning("[get_required_workflow] origin missing in session data")

    if not company_id:
        logger.warning("[get_required_workflow] company_id missing in session data")

    if not KNOWLEDGE_BASE_API_KEY:
        logger.warning("[get_required_workflow] KNOWLEDGE_BASE_API_KEY is not set.")


    payload = {
        "query": title,
        "company_id": company_id,
        "index_name": "hrms_index",
    }

    headers = {
        "Authorization": f"{KNOWLEDGE_BASE_API_KEY}",
        "Content-Type": "application/json",
        "X-Origin": origin
    }

    url = f"{KNOWLEDGE_BASE_URL}/search"

    try:
        # Use POST with JSON body for search queries
        response = requests.post(url=url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        hrms_info_json = response.json()
        # logger.debug(f"[get_required_workflow] fetched HRMS info: {hrms_info_json}")
        return hrms_info_json
    except requests.RequestException as e:
        logger.error(f"[get_required_workflow] request error: {e}", exc_info=True)
        return {"error": "Failed to fetch HRMS workflow", "details": str(e)}
    except ValueError as e:
        # JSON decoding error
        logger.error(f"[get_required_workflow] invalid JSON response: {e}", exc_info=True)
        return {"error": "Invalid response from HRMS service"}



async def initiate_hrms_workflow_questionnaire_agent(
    session_id: str,
    profile_block: str,
    company_id: str,
    app_name: str,
    origin: str,
    preloaded_context: Optional[str],
    mode: str = "web"
):
    try:
        logger.info("Setting up HRMS Workflow Questionnaire Agent")

        # Use correct agent name for LLM credentials
        model = get_llm_engine('hrms_questionnaire_workflow_agent', company_id, app_name, origin)

        date = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

        async def load_context(callback_context: CallbackContext):
 
            return await save_data_in_hrms_context(date, profile_block, callback_context, preloaded_context)

        # Load dynamic instructions and description
        agent_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="hrms_questionnaire_workflow_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=profile_block,
            preloaded_context=preloaded_context,
            mode=mode
        )

        agent = Kivo_LLMAgent(
            name="hrms_questionnaire_workflow_agent",
            model=model,
            instruction=agent_instructions,
            description=agent_prompt_service.get_agent_description("hrms_questionnaire_workflow_agent", company_id),
            output_key="final_summary",
            tools=[get_required_workflow],
            before_agent_callback=load_context,
            after_agent_callback=after_agent_invocation_callback_context,
            before_tool_callback=simple_before_tool_modifier,
            after_tool_callback=simple_after_tool_modifier,
        )
        return agent
    except Exception as e:
        logger.error(f"Error in initiate_hrms_workflow_questionnaire_agent: {e}", exc_info=True)
        return None
