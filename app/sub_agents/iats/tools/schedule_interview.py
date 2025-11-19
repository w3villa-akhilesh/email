from typing import Dict, Any
from datetime import datetime
import json
import httpx
from google.adk.tools.tool_context import ToolContext
from app.utils.logger import logger
from app.services.redis_common_state import get_session_data
from app.sub_agents.iats.interview_context import fetch_interview_detail_from_elasticsearch, fetch_platform_details_from_elasticsearch

app_name = "iats_sequential_flow"
def _validate_interview_inputs(confirmation: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Validate the interview scheduling inputs.
    
    Args:
        confirmation: User confirmation (yes/no)
        tool_context: Tool context containing state information
        
    Returns:
        Dict with validation result
    """
    interview_details = tool_context.state.get("interview_details")
    if not interview_details:
        return {"status": "fail", "message": "No interview details found. Please provide interview details first."}
    VALID_CONFIRMATIONS = ["yes", "y", "confirm", "ok"]
    if confirmation.lower() not in VALID_CONFIRMATIONS:
        return {"status": "fail", "message": "Interview scheduling cancelled."}
    
    return {"status": "success"}

def _get_applicant_id_from_session(session_id: str) -> Dict[str, Any]:
    """
    Get applicant ID from session data.
    
    Args:
        session_id: Session ID
        
    Returns:
        Dict with applicant ID or error
    """
    try:
        session_data = get_session_data(session_id, app_name)
        
        # Try to get applicant ID from selected_job_applicant_ids_and_data
        selected_data = session_data.get("selected_job_applicant_ids_and_data")
        if selected_data:
            try:
                selected_data_parsed = json.loads(selected_data) if isinstance(selected_data, str) else selected_data
                if isinstance(selected_data_parsed, list) and len(selected_data_parsed) > 0:
                    # Get the first applicant ID
                    applicant_id = selected_data_parsed[0].get("id")
                    if applicant_id:
                        return {"status": "success", "applicant_id": applicant_id}
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to parse selected_job_applicant_ids_and_data: {e}")
        
        # Fallback: try to get from job_applicant_id directly
        applicant_id = session_data.get("job_applicant_id")
        if applicant_id:
            return {"status": "success", "applicant_id": applicant_id}
            
        return {"status": "fail", "message": "Applicant ID not found in session data"}
        
    except Exception as e:
        logger.error(f"Error getting applicant ID from session: {e}")
        return {"status": "fail", "message": f"Error retrieving applicant ID: {str(e)}"}

def _get_interview_process_id(interview_rounds: list, interview_type: str) -> Dict[str, Any]:
    """
    Get interview process ID from interview rounds based on interview type.
    
    Args:
        interview_rounds: List of interview rounds from Elasticsearch
        interview_type: The interview type to match
        
    Returns:
        Dict with interview process ID or error
    """
    try:
        for round_data in interview_rounds:
            interview_process = round_data.get("interview_process", {})
            round_type = interview_process.get("round_type")
            
            if round_type and round_type.lower() == interview_type.lower():
                interview_process_id = interview_process.get("id")
                if interview_process_id:
                    return {"status": "success", "interview_process_id": interview_process_id}
        
        return {"status": "fail", "message": f"Interview process ID not found for type: {interview_type}"}
        
    except Exception as e:
        logger.error(f"Error getting interview process ID: {e}")
        return {"status": "fail", "message": f"Error retrieving interview process ID: {str(e)}"}

def _get_interviewer_id(interview_rounds: list, interview_type: str, selected_interviewer_name: str) -> Dict[str, Any]:
    """
    Get interviewer ID from interview rounds based on selected interviewer names.
    
    Args:
        interview_rounds: List of interview rounds from Elasticsearch
        interview_type: The interview type
        selected_interviewer_name: Comma-separated list of interviewer names
        
    Returns:
        Dict with interviewer ID or error
    """
    try:
        # Get interviewers for the specific interview type
        for round_data in interview_rounds:
            interview_process = round_data.get("interview_process", {})
            round_type = interview_process.get("round_type")
            if round_type and round_type.lower() == interview_type.lower():
                interviewers = round_data.get("interviewers", [])
                # Build a simple list of interviewer names for this round
                available_names = _build_available_interviewer_names(interviewers)
                # Parse selected interviewer names
                selected_names = [name.strip() for name in selected_interviewer_name.split(",")] if selected_interviewer_name else []
                # Try to find a matching interviewer id for any of the provided names
                for interviewer in interviewers:
                    if isinstance(interviewer, dict):
                        full_name = interviewer.get("full_name", "")
                        if full_name in selected_names:
                            interviewer_id = interviewer.get("id")
                            if interviewer_id:
                                return {"status": "success", "interviewer_id": interviewer_id}
                    else:
                        if str(interviewer) in selected_names:
                            return {"status": "success", "interviewer_id": interviewer}
                # No match found for provided names in this round -> return names for guidance
                return {
                    "status": "info_needed",
                    "message": f"Selected interviewer not found for '{interview_type}'. These are the interviewers for this interview round type.",
                    "available_interviewer_names": available_names
                }
        # Round type not found
        return {
            "status": "fail",
            "message": f"Interview round type '{interview_type}' not found."
        }
    except Exception as e:
        logger.error(f"Error getting interviewer ID: {e}")
        return {"status": "fail", "message": f"Error retrieving interviewer ID: {str(e)}"}

def _build_available_interviewer_names(interviewers: list) -> list:
    """
    Build a list of available interviewer names from interviewer data.
    
    Args:
        interviewers: List of interviewer data (dict or string)
        
    Returns:
        List of interviewer names
    """
    available_names = []
    for interviewer in interviewers:
        if isinstance(interviewer, dict):
            name_value = interviewer.get("full_name", "")
            if name_value:
                available_names.append(name_value)
        else:
            available_names.append(str(interviewer))
    return available_names


def _get_platform_tag_id(platforms: list, platform_name: str) -> Dict[str, Any]:
    """
    Get platform tag ID from platforms list based on platform name.
    
    Args:
        platforms: List of platforms from Elasticsearch
        platform_name: The platform name to match
        
    Returns:
        Dict with platform tag ID or error
    """
    try:
        for platform in platforms:
            if platform.get("name", "").lower() == platform_name.lower():
                platform_tag_id = platform.get("id")
                if platform_tag_id:
                    return {"status": "success", "platform_tag_id": platform_tag_id}
        
        return {"status": "fail", "message": f"Platform tag ID not found for: {platform_name}"}
        
    except Exception as e:
        logger.error(f"Error getting platform tag ID: {e}")
        return {"status": "fail", "message": f"Error retrieving platform tag ID: {str(e)}"}

def _get_session_and_validate(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Get session data and validate required fields.
    
    Args:
        tool_context: Tool context containing state information
        
    Returns:
        Dict with session data or error
    """
    try:
        session_id = tool_context.state.get("session_id")
        if not session_id:
            return {"status": "fail", "message": "Session ID not found in context"}
        
        session_data = get_session_data(session_id, app_name)
        company_id = session_data.get("company_id")
        token = session_data.get("token")
        origin_url = session_data.get("origin")
        
        if not company_id:
            return {"status": "fail", "message": "Company ID not found in session data"}
            
        return {
            "status": "success",
            "session_id": session_id,
            "session_data": session_data,
            "company_id": company_id,
            "token": token,
            "origin_url": origin_url
        }
    except Exception as e:
        logger.error(f"Error getting session data: {e}")
        return {"status": "fail", "message": f"Error retrieving session data: {str(e)}"}


async def _gather_all_required_data(session_data: dict, company_id: str, session_id: str, interview_details: dict) -> Dict[str, Any]:
    """
    Gather all required data from various sources (session, Elasticsearch).
    
    Args:
        session_data: Session data from Redis
        company_id: Company ID
        session_id: Session ID
        interview_details: Interview details from tool context
        
    Returns:
        Dict with all required data or error
    """
    try:
        # Get applicant ID
        logger.info("Getting applicant ID from session data...")
        applicant_result = _get_applicant_id_from_session(session_id)
        if applicant_result["status"] != "success":
            return applicant_result
        job_applicant_id = applicant_result["applicant_id"]
        logger.info(f"Found applicant ID: {job_applicant_id}")

        # Get job profile ID
        job_profile = session_data.get("job_profile_data")
        job_profile_id = None
        if job_profile:
            try:
                job_profile_data = json.loads(job_profile)
                job_profile_id = job_profile_data.get("id")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse job profile data: {e}")
                # Fallback: use job_profile_id from session_data

        # Fetch interview details from Elasticsearch
        logger.info("Fetching interview details from Elasticsearch...")
        interview_data = await fetch_interview_detail_from_elasticsearch(
            company_id=company_id,
            session_id=session_id,
            job_profile_id=job_profile_id
        )
        
        if not interview_data.get("success"):
            return {"status": "fail", "message": "Failed to fetch interview details from Elasticsearch"}

        interview_rounds = interview_data.get("interview_rounds", [])

        # Get interview process ID
        logger.info("Getting interview process ID...")
        interview_process_result = _get_interview_process_id(
            interview_rounds, 
            interview_details.get("interview_type")
        )
        if interview_process_result["status"] != "success":
            return interview_process_result
        interview_process_id = interview_process_result["interview_process_id"]
        logger.info(f"Found interview process ID: {interview_process_id}")

        # Get interviewer ID
        logger.info("Getting interviewer ID...")
        interviewer_result = _get_interviewer_id(
            interview_rounds,
            interview_details.get("interview_type"),
            interview_details.get("selected_interviewer_name")
        )
        if interviewer_result["status"] != "success":
            return interviewer_result
        interviewer_id = interviewer_result["interviewer_id"]
        logger.info(f"Found interviewer ID: {interviewer_id}")

        # Fetch platform details from Elasticsearch
        logger.info("Fetching platform details from Elasticsearch...")
        platform_data = await fetch_platform_details_from_elasticsearch(company_id)
        
        if not platform_data.get("success"):
            return {"status": "fail", "message": "Failed to fetch platform details from Elasticsearch"}

        platforms = platform_data.get("platforms", [])

        # Get platform tag ID
        logger.info("Getting platform tag ID...")
        platform_result = _get_platform_tag_id(
            platforms, 
            interview_details.get("platform_name")
        )
        if platform_result["status"] != "success":
            return platform_result
        platform_tag_id = platform_result["platform_tag_id"]
        logger.info(f"Found platform tag ID: {platform_tag_id}")

        return {
            "status": "success",
            "job_applicant_id": job_applicant_id,
            "interview_process_id": interview_process_id,
            "interviewer_id": interviewer_id,
            "platform_tag_id": platform_tag_id
        }
        
    except Exception as e:
        logger.error(f"Error gathering required data: {e}", exc_info=True)
        return {"status": "fail", "message": f"Error gathering required data: {str(e)}"}


def _build_api_payload(interview_details: dict, job_applicant_id: str, interview_process_id: str, 
                      interviewer_id: str, platform_tag_id: str) -> dict:
    """
    Build the API payload for interview scheduling.
    
    Args:
        interview_details: Interview details
        job_applicant_id: Job applicant ID
        interview_process_id: Interview process ID
        interviewer_id: Interviewer ID
        platform_tag_id: Platform tag ID
        
    Returns:
        API payload dict
    """
    # Format datetime for API
    schedule_datetime = _format_datetime_for_api(
        interview_details.get("schedule_date"),
        interview_details.get("schedule_time")
    )

    # Build API payload
    payload = {
        "job_applicant_id": job_applicant_id,
        "interview_process_id": interview_process_id,
        "send_email": True,
        "applicant_interview_process_round": {
            "schedule_date": schedule_datetime,
            "schedule_time": schedule_datetime,
            "interviewer_id": interviewer_id,
            "status": "scheduled",
            "platform_tag_id": platform_tag_id,
            "platform_id": interview_details.get("platform_detail")
        }
    }

    logger.info(f"API Payload: {json.dumps(payload, indent=2)}")
    return payload


async def _make_api_call_and_handle_response(payload: dict, token: str, origin_url: str, 
                                           interview_details: dict, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Make the API call and handle the response.
    
    Args:
        payload: API payload
        token: Authentication token
        origin_url: Origin URL
        interview_details: Interview details
        tool_context: Tool context
        
    Returns:
        Dict with API response result
    """
    try:
        # Get authentication data from session
        if not token:
            return {"status": "fail", "message": "Authentication data not found in session"}

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        # Make API call
        api_url = f"{origin_url}/api/v1/applicant_interview_process_rounds"
        logger.info(f"Making API call to: {api_url}")

        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, headers=headers, json=payload)
            
            # Log response safely
            try:
                response_json = response.json() if response.content else {}
            except json.JSONDecodeError as e:
                logger.warning(f"Response is not valid JSON: {response.text}")
                response_json = {}
            
            if response.status_code in [200, 201]:
                logger.info(f"Interview scheduled successfully. Status Code: {response.status_code}")
                
                # Update interview details status
                interview_details["status"] = "scheduled"
                interview_details["scheduled_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                interview_details["api_response"] = response_json
                tool_context.state["interview_details"] = interview_details

                # Create success message
                if isinstance(interview_details.get("selected_interviewer_name"), str):
                    interviewer_names = [name.strip() for name in interview_details["selected_interviewer_name"].split(",")]
                else:
                    interviewer_names = interview_details.get("selected_interviewer_name", [])

                success_message = f"""
                Interview Scheduled Successfully!

                **Date**: {interview_details.get('schedule_date')}
                **Time**: {interview_details.get('schedule_time')}
                **Interview Type**: {interview_details.get('interview_type')}
                **Platform**: {interview_details.get('platform_name')} (ID: {interview_details.get('platform_id')})
                **Interviewers**: {', '.join(interviewer_names)}
                **Scheduled At**: {interview_details.get('scheduled_at')}

                The interview has been scheduled and notifications will be sent to all participants.
                """.strip()

                return {
                    "status": "success",
                    "message": "Interview scheduled successfully.",
                    "interview_details": interview_details,
                    "preview": success_message,
                    "api_response": response_json
                }
            else:
                logger.error(f"Interview scheduling failed. Status Code: {response.status_code}, Response: {response.text}")
                return {
                    "status": "fail",
                    "message": f"Failed to schedule interview. Server responded with status {response.status_code}.",
                    "details": response.text
                }

    except httpx.RequestError as e:
        logger.error(f"HTTP request error during interview scheduling: {e}", exc_info=True)
        return {"status": "fail", "message": "Failed to schedule interview due to network error."}
    except Exception as e:
        logger.error(f"Error in API call: {e}", exc_info=True)
        return {"status": "fail", "message": "An unexpected error occurred during API call."}


def _format_datetime_for_api(date_str: str, time_str: str) -> str:
    """
    Format date and time strings to ISO datetime format for API.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        time_str: Time in HH:MM format
        
    Returns:
        ISO datetime string
    """
    try:
        # Combine date and time
        datetime_str = f"{date_str}T{time_str}:00"
        return datetime_str
    except Exception as e:
        logger.error(f"Error formatting datetime: {e}")
        return f"{date_str}T{time_str}:00"

async def schedule_interview(confirmation: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Schedule the interview using the collected details and make API call.
    
    Args:
        confirmation: User confirmation (yes/no)
        tool_context: Tool context containing state information
        
    Returns:
        Dict containing the scheduling result
    """
    logger.info("Processing interview scheduling...")
    logger.debug(f"Confirmation received: {confirmation}")

    try:
        # Step 1: Validate inputs
        logger.info("Validating interview inputs...")
        validation_result = _validate_interview_inputs(confirmation, tool_context)
        if validation_result["status"] != "success":
            logger.warning("Interview input validation failed.")
            return validation_result

        # Step 2: Get interview details from tool context state
        interview_details = tool_context.state.get("interview_details")
        logger.info(f"Retrieved interview details from context: {interview_details}")

        # Step 3: Get session data and validate
        session_result = _get_session_and_validate(tool_context)
        if session_result["status"] != "success":
            return session_result
        
        session_data = session_result["session_data"]
        company_id = session_result["company_id"]
        token = session_result["token"]
        origin_url = session_result["origin_url"]

        # Step 4: Gather all required data from various sources
        data_result = await _gather_all_required_data(session_data, company_id, session_result["session_id"], interview_details)
        if data_result["status"] != "success":
            return data_result

        # Step 5: Build API payload
        payload = _build_api_payload(
            interview_details,
            data_result["job_applicant_id"],
            data_result["interview_process_id"],
            data_result["interviewer_id"],
            data_result["platform_tag_id"]
        )

        # Step 6: Make API call and handle response
        return await _make_api_call_and_handle_response(payload, token, origin_url, interview_details, tool_context)

    except Exception as e:
        logger.error(f"Unhandled exception in schedule_interview: {e}", exc_info=True)
        return {
            "status": "fail", 
            "message": "An unexpected error occurred while scheduling the interview."
        }
