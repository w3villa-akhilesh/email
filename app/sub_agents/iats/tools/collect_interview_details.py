from typing import Dict, Any, Optional
from datetime import datetime
import json
from google.adk.tools.tool_context import ToolContext
from app.utils.logger import logger
from app.services.redis_common_state import get_session_data
from app.sub_agents.iats.interview_context import fetch_interview_detail_from_elasticsearch

app_name = "iats_sequential_flow"

def validate_interview_details(schedule_date: str, schedule_time: str, platform_name: str, 
                              platform_detail: str, interview_type: str) -> tuple[bool, list]:
    """
    Validate required interview details and return validation status.
    
    Args:
        schedule_date: Interview date
        schedule_time: Interview time
        platform_name: Platform for interview
        platform_detail: Platform access details
        interview_type: Type of interview
        
    Returns:
        Tuple of (is_valid, missing_fields_list)
    """
    missing_fields = []
    if not schedule_date:
        missing_fields.append("schedule date")
    if not schedule_time:
        missing_fields.append("schedule time")
    if not platform_name:
        missing_fields.append("platform name")
    if not platform_detail:
        missing_fields.append("platform detail")
    if not interview_type:
        missing_fields.append("interview type")
    
    return len(missing_fields) == 0, missing_fields


def format_interviewer_info(available_interviewers: list) -> tuple[str, list]:
    """
    Format interviewer information for display and return formatted string and list.
    
    Args:
        available_interviewers: List of interviewer data (dict or string)
        
    Returns:
        Tuple of (formatted_info_string, interviewer_info_list)
    """
    interviewer_info_list = []
    
    for interviewer in available_interviewers:
        if isinstance(interviewer, dict):
            full_name = interviewer.get("full_name", "")
            designation = interviewer.get("designation", "N/A")
            email = interviewer.get("email", "N/A")
            interviewer_info_list.append(f"- {full_name} ({designation}) - {email}")
        else:
            # Handle case where interviewer might be a string
            interviewer_info_list.append(f"- {interviewer}")
    
    interviewer_info = "\n".join(interviewer_info_list)
    return interviewer_info, interviewer_info_list


def handle_interviewer_selection(available_interviewers: list, interview_type: str, interview_data: dict) -> dict:
    """
    Handle the interviewer selection logic when no interviewer is selected.
    
    Args:
        available_interviewers: List of available interviewers
        interview_type: Type of interview
        interview_data: Interview data from Elasticsearch
        
    Returns:
        Dict with status and appropriate message/data
    """
    if available_interviewers:
        interviewer_info, _ = format_interviewer_info(available_interviewers)
        
        return {
            "status": "info_needed",
            "message": f"""
            Available interviewers for {interview_type}:

            {interviewer_info}

            Please select one or more interviewers from the above list and provide their names separated by commas.
            """.strip(),
            "available_interviewers": available_interviewers,
            "requires_interviewer_selection": True
        }
    else:
        return {
            "status": "error",
            "message": f"No interviewers found for interview type '{interview_type}'. Please check the interview type or contact the administrator.",
            "available_interview_types": interview_data.get("interview_details", [])
        }


def get_interviewers_for_type(interview_rounds: list, interview_type: str) -> list:
    """
    Get interviewer names for a specific interview type from interview rounds.
    
    Args:
        interview_rounds: List of interview rounds from Elasticsearch
        interview_type: The specific interview type to find interviewers for
        
    Returns:
        List of interviewer dictionaries for the specified interview type
    """
    for round_data in interview_rounds:
        interview_process = round_data.get("interview_process", {})
        round_type = interview_process.get("round_type")
        
        if round_type and round_type.strip().lower() == interview_type.strip().lower():
            return round_data.get("interviewers", [])
    
    return []

async def collect_interview_details(
    session_id: str,
    schedule_date: str,
    schedule_time: str,
    platform_name: str,
    platform_detail: str,
    interview_type: str,
    selected_interviewer_name: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Collect interview scheduling details from the user.
    
    Args:
        session_id: The session id of the user
        schedule_date: The date for the interview (YYYY-MM-DD format)
        schedule_time: The time for the interview (HH:MM format)
        platform_name: Name of the interview platform (e.g., Zoom, Google Meet)
        platform_detail: Access detail for the interview (meeting link, location, or phone number as per platform_name)
        interview_type: Type of interview (e.g., Technical Round, HR Round)
        selected_interviewer_name: Name of the selected interviewer
        tool_context: Tool context containing state information
        
    Returns:
        Dict containing the collected interview details and confirmation status
    """
    try:
        logger.info(f"Collecting interview details - Type: {interview_type}, Date: {schedule_date}, Time: {schedule_time}, Platform: {platform_name}, Detail: {platform_detail}, Interviewer: {selected_interviewer_name}")

        # Validate required fields
        is_valid, missing_fields = validate_interview_details(
            schedule_date, schedule_time, platform_name, platform_detail, interview_type
        )

        if not is_valid:
            logger.debug(f"Missing required fields: {missing_fields}")
            return {
                "status": "info_needed",
                "message": f"Please provide: {', '.join(missing_fields)}",
                "required_fields": {
                    "schedule_date": "Format: YYYY-MM-DD",
                    "schedule_time": "Format: HH:MM",
                    "platform_name": "e.g., Zoom, Google Meet, Teams",
                    "platform_detail": "Access detail for the interview",
                    "interview_type": "e.g., Technical Round, HR Round",
                    "selected_interviewer_name": "Name of the selected interviewer"
                }
            }

        # Get session data to extract company_id, session_id, and job_profile_id
        
        session_data = get_session_data(session_id, app_name)
        company_id = session_data.get("company_id")
        job_profile_id = session_data.get("job_profile_id")
        job_profile = session_data.get("job_profile_data")
        
        if job_profile:
            try:
                job_profile_data = json.loads(job_profile)
                job_profile_id = job_profile_data.get("id")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse job profile data: {e}")
                # Fallback: use job_profile_id from session_data
        
        # Fetch interview details from Elasticsearch
        interview_data = await fetch_interview_detail_from_elasticsearch(
            company_id=company_id,
            session_id=session_id,
            job_profile_id=job_profile_id
        )
        
        available_interviewers = []
        if interview_data.get("success") and interview_data.get("interview_rounds"):
            available_interviewers = get_interviewers_for_type(
                interview_data["interview_rounds"], 
                interview_type
            )

        # If no interviewers selected, show available interviewers for this interview type
        if not selected_interviewer_name:
            return handle_interviewer_selection(available_interviewers, interview_type, interview_data)

        # Create interview details object
        interview_details = {
            "schedule_date": schedule_date,
            "schedule_time": schedule_time,
            "interview_type": interview_type,
            "platform_name": platform_name,
            "platform_detail": platform_detail,
            "selected_interviewer_name": selected_interviewer_name,
            "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "draft"
        }
        
        # Save interview details in tool context state
        tool_context.state["interview_details"] = interview_details
        logger.info(f"Interview details collected and saved: {interview_details}")
        
        # Create confirmation message
        if isinstance(selected_interviewer_name, str):
            # If selected_interviewer_name is a string, split by comma
            interviewer_names = [name.strip() for name in selected_interviewer_name.split(",")]
        else:
            # If it's already a list of dictionaries
            interviewer_names = []
            for interviewer in selected_interviewer_name:
                if isinstance(interviewer, dict):
                    interviewer_names.append(interviewer.get("full_name", ""))
                else:
                    interviewer_names.append(str(interviewer))
        
        confirmation_message = f"""
                Interview Details Collected:

                **Date**: {schedule_date}
                **Time**: {schedule_time}
                **Interview Type**: {interview_type}
                **Platform**: {platform_name} (Detail: {platform_detail})
                **Interviewers**: {', '.join(interviewer_names)}

                Please confirm if these details are correct. Type 'yes' to schedule the interview or 'no' to modify the details.
        """.strip()
        
        return {
            "status": "success",
            "message": "Details collected successfully. Please review and confirm:",
            "interview_details": interview_details,
            "preview": confirmation_message
        }
        
    except Exception as e:
        logger.error(f"Error collecting interview details: {e}", exc_info=True)
        return {
            "status": "error",
            "message": "Failed to collect interview details. Please try again.",
            "error": str(e)
        }
