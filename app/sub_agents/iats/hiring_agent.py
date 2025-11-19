from app.services.iats_lifecycle_hooks import before_agent_invocation_callback_context, after_agent_invocation_callback_context, simple_after_tool_modifier, simple_before_tool_modifier, after_model_response_callback
from app.utils.logger import logger
from google.adk.agents.llm_agent import LlmAgent
from app.services.llm_engine import get_llm_engine
from datetime import datetime
from app.utils.prompt import HIRING_AGENT_PROMPT
from app.services.agent_prompt_service import agent_prompt_service
from app.utils.memory_utils import memorize
from google.adk.tools.tool_context import ToolContext
from app.services.mcp_connection import connect_to_mcp_server
from app.core.constants import CANDIDATE_IATS_AGENT_URL
import httpx
import json
from app.services.redis_common_state import get_session_data
from typing import Optional, Union
import os 
from dotenv import load_dotenv
load_dotenv()
# This agent is responsible for handling hiring-related queries such as interview scheduling,
# candidate stage updates, offer generation, etc.

async def initiate_hiring_agent(session_id, company_id=None, app_name=None, origin=None):
    """Initialises and returns the hiring_agent LlmAgent instance.

    Args:
        session_id (str): Unique session identifier coming from parent agent.
        company_id (int): Company ID for dynamic prompt generation.
        app_name (str): Application name.
        origin (str): Origin of the request.

    Returns:
        LlmAgent | None: Configured agent or None on error.
    """
    try:
        logger.debug("Initiating hiring_agent with dummy local tools …")

        # Prepare llm model
        hiring_agent_model = get_llm_engine('hiring_agent', company_id)
        date = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

        candidate_iats_toolset = await connect_to_mcp_server(CANDIDATE_IATS_AGENT_URL, tool_filter=["get_hiring_candidates_by_skill"], session_id=session_id)

        # Local tool list (no external MCP dependence)
        all_tools = [
            memorize,
            create_job_profile,
            get_all_jobs,
            search_job_profile,
            fetch_job_applicants_detail_by_job_profile,
            match_applicants_with_job_profile,
        ] + candidate_iats_toolset

        # Get dynamic instructions for hiring agent
        hiring_agent_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="hiring_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=None,
            preloaded_context=None,
            mode="web",
            origin=origin
        )

        hiring_agent = LlmAgent(
            name="hiring_agent",
            model=hiring_agent_model,
            instruction=hiring_agent_instructions,
            description=agent_prompt_service.get_agent_description("hiring_agent", company_id),
            output_key="hiring_info",
            before_agent_callback=before_agent_invocation_callback_context,
            after_agent_callback=after_agent_invocation_callback_context,
            before_tool_callback=simple_before_tool_modifier,
            after_tool_callback=simple_after_tool_modifier,
            tools=all_tools,
            after_model_callback=after_model_response_callback
        )

        return hiring_agent

    except Exception as e:
        logger.error(f"Error in initiate_hiring_agent: {e}", exc_info=False)
        return None

    finally:
        # No external connections to close when using dummy tools
        pass

# ---------------- Dummy Tool Implementations ---------------- #

# Each tool mimics the signature expected by Google ADK tool execution:
# async def tool_name(tool_context: ToolContext, <params>) -> dict


async def get_all_jobs(tool_context: ToolContext, filter_term: str = "") -> dict:
    """Return a list of dummy job profiles."""
    jobs = [
        {"id": "JP-001", "title": "Software Engineer"},
        {"id": "JP-002", "title": "Data Scientist"},
    ]
    # Simple filter by title keyword
    if filter_term:
        jobs = [job for job in jobs if filter_term.lower() in job["title"].lower()]
    return {"status": "success", "jobs": jobs}


async def search_job_profile(tool_context: ToolContext, query: str) -> dict:
    """Search dummy job profiles by query string."""
    return await get_all_jobs(tool_context, query)  # Re-use filter logic


async def fetch_job_applicants_detail_by_job_profile(tool_context: ToolContext, job_profile_id: str) -> dict:
    """Return dummy applicant previews for a given profile id."""
    applicants_preview = [
        {"name": "Alice", "skills": ["Python", "Django"], "experience": 3},
        {"name": "Bob", "skills": ["Java", "Spring"], "experience": 4},
    ]
    return {
        "status": "success",
        "applicants_preview": applicants_preview,
        "url_for_full_applicant_list": f"https://example.com/applicants?jp={job_profile_id}",
    }


async def get_hiring_candidates_by_skill(tool_context: ToolContext, skills: str) -> dict:
    """Return a dummy redis-style key representing fetched candidates by skill."""
    # Simulate generating a key
    job_applicants_key = f"JAK-{skills.replace(' ', '').upper()}-1234"
    return {"status": "success", "job_applicants_key": job_applicants_key, "total_count": 100}


# tool to send job profile and job applicants to kivo server, applicants are retrieved from redis which were saved in mcp.

def match_source_with_new_job_profile(session_id: str, confirmation_intent: str) -> Union[dict, None]:
    """
    Matches existing source with a new job profile by sending session data to an external API.

    Args:
        session_id (str): Redis session ID used to retrieve stored job/applicant info.
        confirmation_intent (str): "yes" to confirm and proceed; any other value will not proceed.

    Returns:
        dict: API response on success,
              or {"message": "..."} if no applicants,
              or None on error.
    """
    try:
        # Check for confirmation from the user before proceeding
        if confirmation_intent.lower() not in ["yes", "true", "okay"]:
            return {"status": "confirmation pending", "message": "please say `yes start matching` to begin process."}

        # can be picked from constants.
        target_api_url = "https://demo.kivo.ai/api/v1/job_profiles_api/track_agent"
        auth_token = os.getenv("TOKEN")

        # Fail early if API token is not available
        if not auth_token:
            logger.error("API token not set.")
            return {"message": "API token missing."}

        # Retrieve session data (should include job profile and applicant ids)
        redis_data = get_session_data(session_id)
        if not redis_data:
            logger.info(f"No data for session: {session_id}")
            return {"message": "no job applicants found."}

        # Extract required information from session data
        job_profile_id = redis_data.get("job_profile_id")
        selected_job_applicant_ids = redis_data.get("selected_job_applicant_ids")
        is_new_job_profile = redis_data.get("is_new_job_profile", True)

        # Ensure required data is present
        if not (job_profile_id and selected_job_applicant_ids):
            logger.info("Missing profile or applicants in session.")
            return {"message": "no job applicants found."}

        # Parse applicant IDs from JSON string
        try:
            job_applicant_ids = json.loads(selected_job_applicant_ids)
            if not isinstance(job_applicant_ids, list):
                raise ValueError()
        except Exception:
            logger.error("Invalid applicant IDs.")
            return {"message": "invalid data for selected job profile."}

        # Prepare the payload as per the target API's requirements
        payload = {
            "job_profile_id": job_profile_id,
            "session_id": session_id,
            "is_new_job_profile": bool(is_new_job_profile),
            "job_applicant_ids": job_applicant_ids
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}"
        }

        # Send POST request to external API
        logger.info(f"Posting match for session {session_id}")
        with httpx.Client() as client:
            response = client.post(target_api_url, json=payload, headers=headers)
            response.raise_for_status()  # Raise error if the response was unsuccessful

        # Construct a matching ID for reference
        matching_id = f"MATCH-{job_profile_id}"

        logger.info("Posted successfully.")
        return {
            "status": "success",
            "message": "Match started successfully",
            "matching_id": matching_id
        }

    except Exception as e:
        # Log the exception with traceback for debugging
        logger.exception(f"Error posting match for session {session_id}: {e}")
        return None


async def match_applicants_with_job_profile(
    tool_context: ToolContext, job_applicants_key: str, job_profile_id: str
) -> dict:
    """Return a dummy matching id linking applicants to a job profile."""
    matching_id = f"MATCH-{job_profile_id}-{job_applicants_key[-4:]}"
    return {"status": "success", "matching_id": matching_id}

async def create_job_profile(
    tool_context: ToolContext,
    session_id: str,
    ) -> dict:
    """
    Invoke this tool for creating job profile. and save the job profile id (jp_id) and is_new_job_profile to True in session state.
    Args:
       - session_id (str): Unique context ID; used to fetch auth token and origin URL.
    Note:
    *Strict rule*: Must use this tool to create story if `preview_confirmed` is true.
    returns:
    - dict:
        - status (str): "success" if job profile created successfully.
        - message (str): Additional context about the operation.
        - jp_id (str): Unique identifier of the newly created job profile.
        - is_new_job_profile (str): "True" if this is a newly created profile.

    """
    job_title = tool_context.state["job_title"]
    job_description = tool_context.state["job_description"]
    job_qualification = tool_context.state["job_qualification"]
    job_minimum_experience = tool_context.state["job_minimum_experience"]
    job_maximum_experience = tool_context.state["job_maximum_experience"]
    job_no_of_positions = tool_context.state["job_no_of_positions"]
    
    logger.debug(f"Invoked create job profile successfully. job_title: {job_title}, job_description: {job_description}, job_qualification: {job_qualification}, job_minimum_experience: {job_minimum_experience}, job_maximum_experience: {job_maximum_experience}, job_no_of_positions: {job_no_of_positions}")
 
    tool_context.state["jp_id"] = "1234"
    tool_context.state["is_new_job_profile"] = "True"
    return {"status":"success", "message":"job created successfully", "jp_id":"1234", "is_new_job_profile":"True"}  

# ------------------------------------------------------------- # 