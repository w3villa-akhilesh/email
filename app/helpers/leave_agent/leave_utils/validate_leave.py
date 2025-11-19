from typing import Dict, Any
from app.utils.logger import logger
import httpx
from app.helpers.leave_agent.leave_utils.get_auth_data import get_session_and_auth_data
from datetime import datetime
from app.services.current_user_dob import get_current_profile_dob


async def validate_leave_date_against_holidays(
    start_date: str, 
    auth_data: Dict[str, Any], 
    leave_category: str
) -> Dict[str, Any]:
    """
    Generic helper function to validate leave dates against holiday list.
    
    For optional leave: Validates that the date IS a valid optional holiday
    For all other leave types: Validates that the date is NOT any type of holiday
    """

    try:
        holiday_url = f"{auth_data['origin']}/api/v1/companies/filtered_holidays"
        async with httpx.AsyncClient() as client:
            response = await client.get(holiday_url, headers=auth_data["headers"])
            response.raise_for_status()
            raw_data = response.json()
            logger.debug(f"Holiday API response: {raw_data}")

            if isinstance(raw_data, dict) and "holidays" in raw_data:
                holiday_list = raw_data["holidays"]
            elif isinstance(raw_data, list):
                holiday_list = raw_data
            else:
                logger.warning("Unexpected holiday API response format, proceeding with empty holiday list.")
                holiday_list = []  # Fallback: assume no holidays

    except Exception as e:
        logger.error(f"Holiday API failed: {e}. Proceeding with empty holiday list.")
        holiday_list = []  # Treat as if there are no holidays

    # Check if leave category is optional
    is_optional_leave = leave_category.lower() in ["optional", "optional leave"]

    if is_optional_leave:
        # For optional leave: Check if the date IS a valid optional holiday
        valid = False
        optional_leave_dates = []
        for holiday in holiday_list:
            if holiday.get("type_of_holiday") == "optional":
                if holiday.get("from_date") == start_date:
                    valid = True
                optional_leave_dates.append(holiday.get("from_date"))
        
        if not valid:
            logger.debug(f"Optional leave date {start_date} is not a valid optional holiday")
            return {
                "valid": False,
                "error": "Date selected is not a valid optional leave date. Please select a different date.",
                "valid_dates": optional_leave_dates
            }
        return {"valid": True}

    else:
        # For all other leave types: Ensure the date is not a holiday
        for holiday in holiday_list:
            if holiday.get("from_date") == start_date:
                holiday_name = holiday.get("name", "Holiday")
                logger.debug(f"Cannot apply leave on {start_date} as it's a holiday ({holiday_name})")
                return {
                    "valid": False,
                    "error": f"Cannot apply leave on {start_date} as it's already a holiday ({holiday_name}). Please select a different date.",
                    "holiday_name": holiday_name
                }
        return {"valid": True}

def validate_leave_category(leave_category: str, leave_balance: list) -> Dict[str, Any]:
    """
    Helper function to validate leave category against available options.
    
    Returns:
        dict: Contains validation result and normalized category name
    """
    if not leave_balance:
        logger.debug("Leave balance information not available, returning error")
        return {
            "valid": False,
            "error": "Leave balance information not available. Please try again."
        }
    
    # Extract valid category names from leave balance data
    valid_categories = [leave.get("name") for leave in leave_balance if leave.get("name")]
    
    if not valid_categories:
        logger.debug("No leave categories available in balance data, returning error")
        return {
            "valid": False,
            "error": "No leave categories available. Please contact HR."
        }
    
    # Check if provided leave category is valid (case-insensitive)
    for valid_category in valid_categories:
        if leave_category.lower() == valid_category.lower():
            return {"valid": True, "category": valid_category}  # Use exact case from API
    
    logger.debug(f"Invalid leave category '{leave_category}', valid options: {valid_categories}")
    return {
        "valid": False,
        "error": f"Invalid leave type. Available options: {', '.join(valid_categories)}"
    }


async def validate_birthday_leave(start_date: str, session_id: str) -> Dict[str, Any]:
    """
    Helper function to validate birthday leave against user's actual birthday.
    
    Returns:
        dict: Contains validation result and any error messages
    """
    try:
        auth_data = await get_session_and_auth_data(session_id)
        if "error" in auth_data:
            logger.debug(f"Authentication error during birthday validation: {auth_data['error']}")
            return {"valid": False, "error": auth_data["error"]}
        
        # Get user's date of birth
        dob_response = await get_current_profile_dob(auth_data["token"], auth_data["origin"])
        logger.debug(f"DOB response: {dob_response}")
        
        if "error" in dob_response:
            logger.debug("Error in DOB response, unable to verify birthday")
            return {"valid": False, "error": "Unable to verify birthday. Please contact HR."}
        
        user_dob = dob_response.get("dob")
        if not user_dob:
            logger.debug("Birthday information not available in profile")
            return {"valid": False, "error": "Birthday information not available. Please contact HR."}
        
        # Parse dates and compare day/month only
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        dob_obj = datetime.strptime(user_dob, "%Y-%m-%d")
        
        if start_date_obj.month != dob_obj.month or start_date_obj.day != dob_obj.day:
            logger.debug(f"Birthday leave date mismatch: requested {start_date}, birthday is {user_dob}")
            return {
                "valid": False,
                "error": f"Birthday leave can only be applied on your birthday ({dob_obj.strftime('%B %d')}). Selected date does not match."
            }
        
        return {"valid": True}
        
    except ValueError as e:
        logger.error(f"Date parsing error: {e}")
        return {"valid": False, "error": "Invalid date format. Please try again."}
    except Exception as e:
        logger.error(f"Birthday validation error: {e}")
        return {"valid": False, "error": "Unable to verify birthday. Please try again."}
