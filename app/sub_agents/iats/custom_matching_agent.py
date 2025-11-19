from typing import List
import uuid
import json
import random

import httpx
from app.models.db_models import CustomMatchingCriteria, CustomMatchingResultsApplicantData
from app.services.iats_lifecycle_hooks import after_agent_invocation_callback_context, before_agent_invocation_callback_context
from app.services.redis_common_state import get_session_data, save_session_data
from app.models.schema import controlled_generation_config
from app.services.iats_lifecycle_hooks import after_agent_invocation_callback_context, before_agent_invocation_callback_context, after_model_response_callback, simple_before_tool_modifier, simple_after_tool_modifier
from app.services.agent_registry import AgentRegistryService
from app.tools.batch_process import get_batch_request_count, process_batch
from app.utils.logger import logger
from app.utils.memory_utils import memorize
from app.utils.prompt import CUSTOM_MATCHING_AGENT_PROMPT, IATS_GLOBAL_INSTRUCTIONS
from app.services.agent_prompt_service import agent_prompt_service
from google.adk.agents.llm_agent import LlmAgent
from app.services.llm_engine import get_llm_credentials_based_on_company_id, get_llm_engine
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.tool_context import ToolContext
from sqlalchemy.orm import Session
from app.services.my_sql_client import get_db
from fastapi.concurrency import run_in_threadpool
from app.models.schema import controlled_generation_config
import asyncio
from pm_board_data.core.config import BASE_URL

app_name = "iats_sequential_flow"

async def get_matching_status(session_id:str, tool_context: ToolContext) -> dict:
    """
    This tool is used to get the status or progress of matching process.
    You can **ONLY** call this tool once you have started a matching job.
    Args:
        session_id (str): str
        tool_context (ToolContext): The context of the tool, containing state variables like
                                    'custom_matching_id'.

    Returns:
        dict: A dictionary containing the status and progress of the job.
    """

    # Get the status of a custom matching job from the database using custom_matching_id. e.g what is status for matching process?
    logger.debug(f"custom_matching_id from tool context : {tool_context.state.get('custom_matching_id')}")

    session_data = get_session_data(session_id, app_name)
    custom_matching_id = session_data.get('custom_matching_id')
    token = session_data.get("token")
    origin = session_data.get("origin")

    if not custom_matching_id:
        logger.error(f"No matching job has been started in the current session: {session_id}")
        return {"status": "completed", "message": "All matching jobs has been completed in the current chat."}

    logger.info(f"Reviewing status for custom_matching_id: {custom_matching_id}")
    matching_status_url = f"{origin}/api/v1/resume_matching/status/{custom_matching_id}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                matching_status_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            logger.debug(f"Matching Status {response.json()}")
            response.raise_for_status()
            return {
                "status_update": response.json()
            }

    except httpx.HTTPError as e:
        logger.error(f"[KIVO ERROR] Failed to fetch matching status: {e}")
        return {"status": "error", "message": "Failed to fetch matching status."}    

    
async def begin_matching_processs(
    custom_matching_id,
    matching_criteria,
    user_id,
    company_id,
    scoring_criteria,
    applicant_ids,
    applicants_list,
    session_id
):
    def insert_criteria() -> int:
        db: Session = next(get_db())
        try:
            entry = CustomMatchingCriteria(
                custom_matching_id = custom_matching_id,
                matching_criteria=matching_criteria,
                user_id=user_id,
                company_id=company_id,
                scoring_criteria=scoring_criteria,
                matching_status="in_progress",
                job_applicant_ids=applicant_ids
            )
            db.add(entry)
            db.commit()
            db.refresh(entry)
            return entry.custom_matching_id
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    await run_in_threadpool(insert_criteria)

    token = get_session_data(session_id, app_name).get("token")
    origin = get_session_data(session_id, app_name).get("origin")

    if not token:
        logger.error("No token found in session data, cannot proceed with matching.")
        return {"status": "error", "message": "No token found, cannot proceed with matching."}
    
    custom_model, llm_key, llm_base_url = get_llm_credentials_based_on_company_id("iats_sequential_flow", company_id, origin)

    hex_llm_key = llm_key.encode("utf-8").hex()

    try:
        applicant_count = len(applicant_ids)
    except TypeError:
        logger.warning("applicant_ids is not iterable or None; defaulting to process_type:sequential")
        applicant_count = 0

    if applicant_count >= 30:
        logger.debug(f"Applicant count: {applicant_count} — using process_type:batch")
        process_type = "batch"
    else:
        logger.debug(f"Applicant count: {applicant_count} — using process_type:sequential")
        process_type = "sequential"

    # send the data cruicial for batch process to kivo server.
    batch_process_payload = {
        "custom_matching_id": custom_matching_id,
        "matching_criteria": str(matching_criteria),
        "scoring_criteria": str(scoring_criteria),
        "resumes": applicant_ids,
        "session_id": str(session_id),
        "process_type": process_type,
        "llm_key": str(hex_llm_key), 
        "llm_type": str(custom_model),
        "llm_base_url": str(llm_base_url)
        }
    
    matching_batch_url = f"{origin.rstrip('/')}/api/v1/resume_matching"
    logger.info(f"matching_batch_url: {matching_batch_url}")
    # matching_batch_url = f"{BASE_URL}/api/v1/resume_matching"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                matching_batch_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json=batch_process_payload,
                timeout=30.0
            )
            if response.status_code == 200:
                logger.info(f"Batch request sent successfully for custom_matching_id: {custom_matching_id}")
            response.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(f"[KIVO ERROR] Failed to send batch request: {e}")
        if getattr(e, "response", None) is not None:
            logger.error(f"Response body: {e.response.text}")
        raise e

    
    # asyncio.create_task(run_batch_in_thread(
    #     resumes=applicants_list,
    #     session_id=session_id,
    #     custom_matching_id=custom_matching_id,
    #     matching_criteria=matching_criteria,
    #     scoring_criteria=scoring_criteria
    # ))

    return custom_matching_id

# use to run matching as a batch process.
# async def run_batch_in_thread(*args, **kwargs):
#     logger.info("Processing in batch started successfully.")
#     await run_in_threadpool(lambda: asyncio.run(process_batch(*args, **kwargs)))


# tool to begin custom matching once applicant data and skills are identified.
async def run_custom_matching(
    session_id: str,
    tool_context: ToolContext
) -> dict:
    """
    Runs a custom matching process asynchronously.
    You **MUST** call matching_criteria_agent and scoring_criteria_agent before you call this tool.
    Args:
        session_id (str): str
    
    Returns:
        dict: Status, message, custom_matching_id to track matching job and matching_url to check the results
    """
    logger.info("Invoking run_custom_matching tool.")
    
    # extract state
    try:
        state = tool_context.state
        matching_criteria = state.get("matching_criteria")
        scoring_criteria = state.get("scoring_criteria")
        company_id = state.get("profile", {}).get("company_id")
        user_id = state.get("user_id")
        logger.debug(f"Extracted from state: company_id={company_id}, user_id={user_id}")

    except Exception as e:
        logger.error(f"Error extracting state from tool_context: {e}", exc_info=True)
        return {"status": "error", "message": "Failed to extract required data from tool context."}
 
    if not matching_criteria:
        logger.warning("Missing matching_criteria in tool_context.state.")
        return {"status": "error", "message": "matching_criteria not found in state, you **MUST** call matching_criteria_agent tool to extract it."}
    
    if not scoring_criteria:
        logger.warning("Missing scoring_criteria in tool_context.state.")
        return {"status": "error", "message": "scoring_criteria not found in state, you **MUST** call scoring_criteria_agent tool to extract it."}

    # extracting resume data from session store
    try:
        session_data = get_session_data(session_id, app_name)
        origin = session_data.get('origin')
        if session_data.get('custom_matching_id'):
            running_custom_matching_id = session_data['custom_matching_id']
            return {
                "status": "in-progress",
                "message": "Matching job is already running. You can ask for status.",
                "custom_matching_id": running_custom_matching_id,
                "matching_url": f"{origin}hrms/agent_matching_job_applicants?matching_id={running_custom_matching_id}"
            }

        selected_data = session_data.get("selected_job_applicant_ids_and_data")

        if not selected_data:
            logger.warning(f"No applicant data found in session store for session_id: {session_id}")
            tool_context.actions.transfer_to_agent = "candidate_iats_agent"
            return {"status": "error", "message": "No applicant data found, you **MUST** call candidate_iats_agent tool to extract it."}
        applicants_list = json.loads(selected_data)

    except json.JSONDecodeError:
        logger.error("Invalid JSON in session store.")
        return {"status": "error", "message": "Failed to process data in matching"}
    
    except Exception as e:
        logger.error(f"Error retrieving session data: {e}", exc_info=True)
        return {"status": "error", "message": "Failed to process data in matching."}

    applicant_ids = [a.get("id") for a in applicants_list if a.get("id")]
    logger.debug(f"Parsed applicant ids: {applicant_ids}")

    # generating matching id
    custom_matching_id = f"custom-{uuid.uuid4().hex[:8]}"
    # update custom_matching_id in tool state
    tool_context.state["custom_matching_id"] = custom_matching_id 

    matching_status_data = {"custom_matching_id": custom_matching_id}
    save_session_data(session_id, matching_status_data)


    # Begin matching process
    try:
        asyncio.create_task(
            run_batch_in_thread(
                custom_matching_id,
                matching_criteria,
                user_id,
                company_id,
                scoring_criteria,
                applicant_ids,
                applicants_list,
                session_id
            )
        )
        logger.info(f"Started custom matching process with ID: {custom_matching_id}")

    except Exception as e:
        logger.error(f"Error in m: {e}", exc_info=True)
        return {"status": "error", "message": "Failed to initiate matching process."}

    return {
        "status": "success",
        "message": "Matching job started successfully. You can ask for status.",
        "custom_matching_id": custom_matching_id,
        "matching_url": f"{origin}hrms/agent_matching_job_applicants?matching_id={custom_matching_id}"
    }

async def run_batch_in_thread(*args, **kwargs):
    logger.info("Processing in batch/sequential started successfully.")
    await run_in_threadpool(lambda: asyncio.run(begin_matching_processs(*args, **kwargs)))


async def download_matching_results(session_id: str, tool_context: ToolContext) -> dict:
    """
    Generates a download link for the custom matching results in the specified format.
    You can **ONLY** call this method only if custom_matching_id is present in state variables.
    If custom_matching_id is not present in state variables, you **MUST** ask user to start a matching job first.
    Args:
        session_id (str): str
        tool_context (ToolContext): The context of the tool, containing arguments like 'file_format'.

    Returns:
        dict: A dictionary containing the download URL or an error message.
    """
    custom_matching_id = tool_context.state.get("custom_matching_id")
    session_data = get_session_data(session_id, app_name)
    origin = session_data.get('origin')
    if not custom_matching_id:
        return {"status": "error", "message": "Can not download matching results, as no matching job has been started yet."}

    file_format = tool_context.state.get("file_format", "csv").lower()
    
    if file_format not in ["csv", "excel"]:
        return {"status": "error", "message": "Unsupported file format. Please choose 'csv' or 'excel'."}

    download_url = f"{origin}hrms/agent_matching_job_applicants/export_{file_format}?matching_id={custom_matching_id}"

    return {
        "status": "success",
        "message": f"Your download link for the matching results in {file_format} format is ready.",
        "download_url": download_url
    }


async def initiate_custom_matching_agent(origin, session_id, company_id, app_name):
    """
    Initializes and returns the custom_matching_agent.

    Args:
        session_id (str): The ID of the session.

    Returns:
        LlmAgent: The initialized custom_matching_agent.
    """
    try:
        logger.debug("Initiating custom_matching_agent...")

        custom_matching_model = get_llm_engine('custom_matching_agent', company_id)

        # Use AgentRegistryService to create sub-agents dynamically
        candidate_iats_agent = await AgentRegistryService.create_agent_instance(
            "candidate_iats_agent",
            origin=origin,
            session_id=session_id,
            company_id=company_id,
            app_name=app_name
        )
        candidate_iats_agent_tool = AgentTool(agent=candidate_iats_agent)

        matching_criteria_agent = await AgentRegistryService.create_agent_instance(
            "matching_criteria_agent",
            origin=origin,
            session_id=session_id,
            company_id=company_id,
            app_name=app_name
        )
        matching_criteria_agent_tool = AgentTool(agent=matching_criteria_agent)

        scoring_criteria_agent = await AgentRegistryService.create_agent_instance(
            "scoring_criteria_agent",
            origin=origin,
            session_id=session_id,
            company_id=company_id,
            app_name=app_name
        )
        scoring_criteria_agent_tool = AgentTool(agent=scoring_criteria_agent)

        # Get dynamic instructions for custom matching agent
        custom_matching_agent_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="custom_matching_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=None,
            preloaded_context=None,
            mode="web",
            origin=origin
        )

        custom_matching_agent = LlmAgent(
            name="custom_matching_agent",
            model=custom_matching_model,
            instruction=f"{IATS_GLOBAL_INSTRUCTIONS}\n{custom_matching_agent_instructions}",
            description=agent_prompt_service.get_agent_description("custom_matching_agent", company_id),
            tools=[run_custom_matching, get_matching_status, download_matching_results, candidate_iats_agent_tool, matching_criteria_agent_tool, scoring_criteria_agent_tool, memorize],
            before_agent_callback=before_agent_invocation_callback_context,
            after_agent_callback=after_agent_invocation_callback_context,
            after_model_callback=after_model_response_callback,
            before_tool_callback=simple_before_tool_modifier,
            after_tool_callback=simple_after_tool_modifier,
            generate_content_config=controlled_generation_config
        )

        return custom_matching_agent

    except Exception as e:
        logger.error(f"Error in initiate_custom_matching_agent: {e}", exc_info=True)
        raise