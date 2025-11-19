import uuid
import json
from app.services.iats_lifecycle_hooks import (
    after_agent_invocation_callback_context, before_agent_invocation_callback_context,
    after_model_response_callback, simple_before_tool_modifier, simple_after_tool_modifier
)
from app.services.redis_common_state import get_session_data, save_session_data
from app.utils.logger import logger
from app.utils.prompt import IATS_GLOBAL_INSTRUCTIONS, JOB_PROFILE_MATCHING_AGENT_PROMPT
from app.services.agent_prompt_service import agent_prompt_service
from google.adk.agents.llm_agent import LlmAgent
from app.services.llm_engine import get_llm_engine
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.tool_context import ToolContext
from app.services.agent_registry import AgentRegistryService
from app.tools.batch_process import process_batch
from fastapi.concurrency import run_in_threadpool
import asyncio

# 2. Tool: Convert job profile to matching criteria
async def job_profile_to_matching_criteria(session_id: str, tool_context: ToolContext) -> dict:
    """
    Convert selected job profile data to matching criteria using matching_criteria_agent.
    Args:
        session_id (str): Session ID
        tool_context (ToolContext): Tool context with selected job profile
    Returns:
        dict: Matching criteria
    """
    try:
        selected_profile = tool_context.state.get('selected_job_profile')
        if not selected_profile:
            return {"status": "error", "message": "No job profile selected. Please select a job profile first using job_profile_agent."}
        # Get session data to extract required parameters
        session_data = get_session_data(session_id)
        profile = session_data.get("profile", {})
        company_id = profile.get("company_id")
        app_name = session_data.get("app_name", "iats_sequential_flow")
        origin = session_data.get("origin", "https://demo.kivo.ai/")
        
        matching_criteria_agent = await AgentRegistryService.create_agent_instance(
            "matching_criteria_agent", 
            session_id=session_id, 
            company_id=company_id, 
            app_name=app_name, 
            origin=origin
        )
        if not matching_criteria_agent:
            return {"status": "error", "message": "Failed to initialize matching_criteria_agent."}
        # Pass the job profile data as input
        result = await matching_criteria_agent.run_tool('process_job_profile', tool_context, job_profile=selected_profile)
        if result.get('status') != 'success' or not result.get('matching_criteria'):
            return {"status": "error", "message": "Failed to extract matching criteria from job profile."}
        tool_context.state['matching_criteria'] = result['matching_criteria']
        return {"status": "success", "matching_criteria": result['matching_criteria']}
    except Exception as e:
        logger.error(f"Error in job_profile_to_matching_criteria: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

# 3. Tool: Run job profile matching (similar to run_custom_matching)
async def run_job_profile_matching(session_id: str, tool_context: ToolContext) -> dict:
    """
    Run the matching process using criteria from the selected job profile.
    Args:
        session_id (str): Session ID
        tool_context (ToolContext): Tool context with matching_criteria and scoring_criteria
    Returns:
        dict: Status and matching job info
    """
    logger.info("Invoking run_job_profile_matching tool.")
    try:
        state = tool_context.state
        matching_criteria = state.get("matching_criteria")
        scoring_criteria = state.get("scoring_criteria")
        company_id = state.get("profile", {}).get("company_id")
        user_id = state.get("user_id")
    except Exception as e:
        logger.error(f"Error extracting state from tool_context: {e}", exc_info=True)
        return {"status": "error", "message": "Failed to extract required data from tool context."}
    if not matching_criteria:
        return {"status": "error", "message": "matching_criteria not found in state. Please extract it from job profile first."}
    if not scoring_criteria:
        return {"status": "error", "message": "scoring_criteria not found in state. Please call scoring_criteria_agent tool to extract it."}
    try:
        session_data = get_session_data(session_id)
        selected_data = session_data.get("selected_job_applicant_ids_and_data")
        if not selected_data:
            tool_context.actions.transfer_to_agent = "candidate_iats_agent"
            return {"status": "error", "message": "No applicant data found. Please extract it using candidate_iats_agent tool."}
        applicants_list = json.loads(selected_data)
    except Exception as e:
        logger.error(f"Error retrieving session data: {e}", exc_info=True)
        return {"status": "error", "message": "Failed to load session data from Redis."}
    applicant_ids = [a.get("id") for a in applicants_list if a.get("id")]
    matching_id = f"job-profile-{uuid.uuid4().hex[:8]}"
    tool_context.state["job_profile_matching_id"] = matching_id
    save_session_data(session_id, {"job_profile_matching_id": matching_id})
    async def insert_and_process():
        # Here you would insert the matching job into DB and start batch processing, similar to custom_matching_agent
        await run_in_threadpool(lambda: process_batch(
            resumes=applicants_list,
            session_id=session_id,
            custom_matching_id=matching_id,
            matching_criteria=matching_criteria,
            scoring_criteria=scoring_criteria
        ))
    asyncio.create_task(insert_and_process())
    return {
        "status": "success",
        "message": "Job profile matching job started successfully. You can ask for status.",
        "job_profile_matching_id": matching_id,
        "matching_url": f"http://demo.kivo.ai/hrms/agent_matching_job_applicants?matching_id={matching_id}"
    }

# 4. Agent initialization
async def initiate_job_profile_matching_agent(session_id: str, company_id=None, app_name=None, origin=None):
    try:
        logger.debug("Initiating job_profile_matching_agent...")
        model = get_llm_engine('interview_scheduler_agent', company_id)
        
        # Use agent registry to create sub-agents dynamically
        job_profile_agent = await AgentRegistryService.create_agent_instance(
            "job_profile_agent", 
            session_id=session_id, 
            company_id=company_id, 
            app_name=app_name, 
            origin=origin
        )
        job_profile_agent_tool = AgentTool(agent=job_profile_agent)
        
        matching_criteria_agent = await AgentRegistryService.create_agent_instance(
            "matching_criteria_agent", 
            session_id=session_id, 
            company_id=company_id, 
            app_name=app_name, 
            origin=origin
        )
        matching_criteria_agent_tool = AgentTool(agent=matching_criteria_agent)
        
        scoring_criteria_agent = await AgentRegistryService.create_agent_instance(
            "scoring_criteria_agent", 
            session_id=session_id, 
            company_id=company_id, 
            app_name=app_name, 
            origin=origin
        )
        scoring_criteria_agent_tool = AgentTool(agent=scoring_criteria_agent)
        
        candidate_iats_agent = await AgentRegistryService.create_agent_instance(
            "candidate_iats_agent", 
            session_id=session_id, 
            company_id=company_id, 
            app_name=app_name, 
            origin=origin
        )
        candidate_iats_agent_tool = AgentTool(agent=candidate_iats_agent)

        # Get dynamic instructions for job profile matching agent
        job_profile_matching_agent_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="job_profile_matching_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=None,
            preloaded_context=None,
            mode="web",
            origin=origin
        )
        
        agent = LlmAgent(
            name="job_profile_matching_agent",
            model=model,
            instruction=job_profile_matching_agent_instructions,
            description=agent_prompt_service.get_agent_description("job_profile_matching_agent", company_id),
            tools=[
                job_profile_to_matching_criteria,
                run_job_profile_matching,
                job_profile_agent_tool,  # sub-agent for job profile selection
                matching_criteria_agent_tool,
                scoring_criteria_agent_tool,
                candidate_iats_agent_tool
            ],
            before_agent_callback=before_agent_invocation_callback_context,
            after_agent_callback=after_agent_invocation_callback_context,
            after_model_callback=after_model_response_callback,
            before_tool_callback=simple_before_tool_modifier,
            after_tool_callback=simple_after_tool_modifier
        )
        return agent
    except Exception as e:
        logger.error(f"Error in initiate_job_profile_matching_agent: {e}", exc_info=True)
        return None 