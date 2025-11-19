from typing import Dict, Any
from google.adk.tools.tool_context import ToolContext
from datetime import datetime
from typing import Literal
from app.helpers.leave_agent.leave_utils.get_auth_data import get_session_and_auth_data
from app.helpers.leave_agent.leave_utils.checking_methods import check_existing_leave_on_date, check_leave_balance_availability
from app.helpers.leave_agent.leave_utils.validate_leave import validate_leave_date_against_holidays, validate_birthday_leave, validate_leave_category
from app.utils.logger import logger

async def collect_leave_details(
    tool_context: ToolContext,
    reason: str,
    start_date: str,
    end_date: str,
    leave_category: str,
    leave_type: Literal["Full Day Leave", "Half Day Leave"]
) -> Dict[str, Any]:
    """
    Collects and validates leave application details.

    Args:
        tool_context (ToolContext): The context of the tool for storing state
        reason (str): Reason for leave
        start_date (str): Start date of leave
        end_date (str): End date of leave
        leave_category (str): Category of leave
        leave_type (str): Literal["Full Day Leave", "Half Day Leave"]

    Returns:
        dict: Validation result and leave details
    """
    logger.info("Collecting leave details...")
    logger.debug(f"Leave category: {leave_category}")
    logger.debug(f"Leave type: {leave_type}")
    logger.debug(f"Start date: {start_date}")
    logger.debug(f"Reason: {reason}")
    logger.debug(f"End date: {end_date}")

    session_id = tool_context.state.get("session_id")
    app_name = tool_context.state.get("app_name")
    
    logger.debug(f"[collect_leave_details] session_id from context: {session_id}")
    logger.debug(f"[collect_leave_details] app_name received is: {app_name}")
    
    if not session_id:
        logger.error("Session ID not found in tool context")
        return {
            "status": "error",
            "message": "Session error. Please try again."
        }

    # Get leave balance from context first to get valid categories
    leave_balance = tool_context.state.get("leave_balance", [])
    valid_categories = [leave.get("name") for leave in leave_balance if leave.get("name")]

    try:
        # check given start date or end date is not sunday
        # Validate that start_date and end_date are not Sundays
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
                if start_date_obj.weekday() == 6:  # Sunday is 6 (Monday is 0)
                    logger.debug(f"Start date {start_date} is a Sunday, preventing leave application")
                    return {
                        "status": "error",
                        "message": f"Leave cannot be applied on Sunday ({start_date}). Please select a weekday."
                    }
            except ValueError:
                logger.debug(f"Invalid start date format: {start_date}")
                return {
                    "status": "error",
                    "message": "Invalid start date format. Use YYYY-MM-DD."
                }
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
                if end_date_obj.weekday() == 6:  # Sunday is 6 (Monday is 0)
                    logger.debug(f"End date {end_date} is a Sunday, preventing leave application")
                    return {
                        "status": "error",
                        "message": f"Leave cannot be applied on Sunday ({end_date}). Please select a weekday."
                    }
                
                # Validate that end date is not in the past
                current_date = datetime.now().date()
                if end_date_obj.date() < current_date:
                    logger.debug(f"End date {end_date} is in the past, preventing leave application")
                    return {
                        "status": "error",
                        "message": f"Leave cannot be applied for past dates. End date ({end_date}) must be today or a future date."
                    }
                    
            except ValueError:
                logger.debug(f"Invalid end date format: {end_date}")
                return {
                    "status": "error",
                    "message": "Invalid end date format. Use YYYY-MM-DD."
                }
        
        # Check if leave already exists on the given date
        if start_date:  # Only check if start_date is provided
            # Get authentication data for API calls
            auth_data = await get_session_and_auth_data(session_id, app_name)
            if "error" in auth_data:
                logger.warning(f"Could not verify existing leaves: {auth_data['error']}")
                # Continue without blocking - this is just a warning check
            else:
                existing_leave_check = await check_existing_leave_on_date(start_date, auth_data, leave_type)
                if existing_leave_check.get("has_existing_leave", False):
                    existing_leaves = existing_leave_check.get("existing_leaves", [])
                    total_leaves = existing_leave_check.get("total_leaves", 0)
                    
                    # Format existing leave details for user
                    leave_summary = []
                    for leave in existing_leaves:
                        leave_summary.append(f"• {leave['category']} ({leave['type']}) - {leave['status']}")
                    
                    logger.debug(f"Leave already exists for {start_date}, blocking application")
                    return {
                        "status": "error",
                        "message": f"Leave already applied for {start_date}. Existing leave(s):\n" + "\n".join(leave_summary) + "\n\nPlease select a different date or contact HR for assistance."
                    }
        
        # Get leave balance from context
        if not leave_balance:
            logger.debug("Leave balance information not available in context")
            return {
                "status": "error",
                "message": "Leave balance information not available. Please try again."
            }

        # Validate leave category
        category_validation = validate_leave_category(leave_category, leave_balance)
        if not category_validation["valid"]:
            logger.debug(f"Leave category validation failed: {category_validation['error']}")
            return {"status": "error", "message": category_validation["error"]}

        leave_category = category_validation["category"]  # Use normalized category name

        # Auto-fill reason for special leave categories
        if leave_category.lower() in ["birthday", "birthday leave"]:
            reason = reason or "Birthday leave"
            # Validate birthday leave
            birthday_validation = await validate_birthday_leave(start_date, session_id)
            if not birthday_validation["valid"]:
                logger.debug(f"Birthday leave validation failed: {birthday_validation['error']}")
                return {"status": "error", "message": birthday_validation["error"]}
                
        elif leave_category.lower() in ["optional", "optional leave"]:
            reason = reason or "Optional holiday"
            # Validate optional leave date
            auth_data = await get_session_and_auth_data(session_id, app_name)
            if "error" in auth_data:
                logger.debug(f"Authentication error for optional leave validation: {auth_data['error']}")
                return {"status": "error", "message": auth_data["error"]}
            
            optional_validation = await validate_leave_date_against_holidays(start_date, auth_data, leave_category)
            if not optional_validation["valid"]:
                logger.debug(f"Optional leave date validation failed: {optional_validation['error']}")
                return {
                    "status": "error", 
                    "message": optional_validation["error"],
                    "valid_dates": optional_validation.get("valid_dates", [])
                }
        
        # Validate leave type
        valid_types = ["Full Day Leave", "Half Day Leave"]
        if leave_type not in valid_types:
            if leave_category and leave_category.lower() in ["birthday", "birthday leave", "optional", "optional leave"]:
                leave_type = "Full Day Leave"
            else:
                logger.debug(f"Invalid leave type: {leave_type}, valid options: {valid_types}")
                return {
                    "status": "error",
                    "message": f"Invalid leave duration. Options: {', '.join(valid_types)}"
                }
        
        # Validate start date format
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            logger.debug(f"Invalid start date format: {start_date}")
            return {
                "status": "error",
                "message": "Invalid date format. Use YYYY-MM-DD."
            }

        # Validate that start date is not in the past
        current_date = datetime.now().date()
        if start_date_obj.date() < current_date:
            logger.debug(f"Start date {start_date} is in the past, preventing leave application")
            return {
                "status": "error",
                "message": f"Leave cannot be applied for past dates. Start date ({start_date}) must be today or a future date."
            }

        # Validate date range if end_date is provided
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
                if end_date_obj.date() < start_date_obj.date():
                    logger.debug(f"End date {end_date} is before start date {start_date}")
                    return {
                        "status": "error",
                        "message": f"End date ({end_date}) cannot be before start date ({start_date}). Please check your dates."
                    }
            except ValueError:
                logger.debug(f"Invalid end date format: {end_date}")
                return {
                    "status": "error",
                    "message": "Invalid end date format. Use YYYY-MM-DD."
                }

        # Universal holiday validation for all leave types
        # Get auth data for holiday validation if not already retrieved
        if leave_category.lower() not in ["optional", "optional leave"]:
            auth_data = await get_session_and_auth_data(session_id, app_name)
            if "error" in auth_data:
                logger.debug(f"Authentication error for holiday validation: {auth_data['error']}")
                return {"status": "error", "message": auth_data["error"]}
            
            # Validate that the date is not a holiday for non-optional leave
            holiday_validation = await validate_leave_date_against_holidays(start_date, auth_data, leave_category)
            if not holiday_validation["valid"]:
                logger.debug(f"Holiday validation failed: {holiday_validation['error']}")
                return {
                    "status": "error", 
                    "message": holiday_validation["error"]
                }

        # Check leave balance availability
        balance_check = check_leave_balance_availability(leave_balance, leave_category, leave_type)
        if balance_check["status"] == "insufficient_balance":
            logger.debug(f"Insufficient leave balance: {balance_check['message']}")
            return {"status": "error", "message": balance_check["message"]}
        elif balance_check["status"] == "error":
            logger.debug(f"Leave balance check error: {balance_check['message']}")
            return {"status": "error", "message": balance_check["message"]}
        
        logger.info(f"Leave balance check passed: {balance_check['message']}")
            # Check for missing fields and return the missing fields
        missing_fields = []
        if not leave_category:
            missing_fields.append("leave category")
        if not start_date:
            missing_fields.append("start date")
        if not reason:
            missing_fields.append("reason for leave")

        if missing_fields:
            logger.debug(f"Missing required fields: {missing_fields}")
            return {
                "status": "info_needed",
                "message": f"Please provide: {', '.join(missing_fields)}",
                "required_fields": {
                    "leave_category": f"Options: {', '.join(valid_categories)}" if valid_categories else "Please contact HR for available leave types",
                    "leave_type": "Options: Full Day Leave, Half Day Leave",
                    "start_date": "Format: YYYY-MM-DD",
                    "reason": "Detailed reason (minimum 5 characters)",
                    "end_date": "Required for multiple days (YYYY-MM-DD format)"
                }
            }
        # Validate start date format
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            logger.debug(f"Invalid start date format during final validation: {start_date}")
            return {
                "status": "error",
                "message": "Invalid date format. Use YYYY-MM-DD."
            }
        leave_details = {
            "leave_category": leave_category,
            "leave_type": leave_type,
            "start_date": start_date,
            "end_date": end_date,
            "reason": reason.strip(),
            "status": "draft"
        }

        tool_context.state["leave_details"] = leave_details
        logger.info(f"Leave details collected successfully: {leave_details}")

        return {
            "status": "success",
            "message": "Details collected successfully. Please review and confirm:",
            "leave_details": leave_details,
            "preview": f"""
                Leave Application Summary:
                • Category: {leave_category}
                • Type: {leave_type}
                • Start Date: {start_date}
                • End Date: {end_date}
                • Reason: {reason}

                Current Leave Balance: {leave_balance}
                Confirm to submit this application.
            """
        }

    except Exception as e:
        logger.error(f"Error collecting leave details: {e}", exc_info=True)
        return {
            "status": "error",
            "message": "Unable to process request. try again."
        }
