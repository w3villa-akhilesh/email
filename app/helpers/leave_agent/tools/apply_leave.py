from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import httpx

from google.adk.tools.tool_context import ToolContext

from app.utils.logger import logger
from app.helpers.leave_agent.leave_utils.get_auth_data import get_session_and_auth_data
from app.helpers.leave_agent.leave_utils.checking_methods import check_leave_balance_availability
from app.helpers.leave_agent.leave_utils.get_employee_id import get_employee_id


def _validate_leave_inputs(confirmation: str, tool_context: ToolContext) -> Optional[Dict[str, Any]]:
    leave_details = tool_context.state.get("leave_details")
    if not leave_details:
        return {"status": "fail", "message": "No leave details found. Please provide application details first."}
    if confirmation.lower() not in ["yes", "y", "confirm", "ok"]:
        return {"status": "fail", "message": "Application cancelled."}
    return None

def _check_leave_balance(tool_context: ToolContext, leave_category: str, leave_type: str) -> Optional[Dict[str, Any]]:
    leave_balance = tool_context.state.get("leave_balance")
    print("leave_balance",leave_balance)
    if not leave_balance:
        return {"status": "fail", "message": "Balance information unavailable. Cannot process application."}
    balance_check = check_leave_balance_availability(leave_balance, leave_category, leave_type)
    print("balance_check",balance_check)
    if balance_check["status"] != "success":
        return {"status": "fail", "message": balance_check["message"]}
    return None

async def _get_employee_info(tool_context: ToolContext, app_name: str) -> Tuple[Optional[Dict[str, Any]], Optional[dict], Optional[str]]:
    session_id = tool_context.state.get("session_id")
    if not session_id:
        return {"status": "fail", "message": "Session error. Please try again."}, None, None
    auth_data = await get_session_and_auth_data(session_id, app_name)
    if "error" in auth_data:
        return {"status": "fail", "message": auth_data["error"]}, None, None
    employee_data = await get_employee_id(auth_data["origin"], auth_data["headers"])
    if "error" in employee_data:
        return {"status": "fail", "message": employee_data["error"]}, None, None
    return None, auth_data, employee_data["employee_id"]

def _get_leave_category_id(leave_balance: list, leave_category: str) -> Optional[str]:
    for leave in leave_balance:
        if leave.get("name", "").lower() == leave_category.lower():
            return leave.get("id")
    return None

def _build_leave_payload(employee_id: str, leave_details: dict, leave_category_id: str) -> dict:
    return {
        "profile": {
            "id": employee_id,
            "leaves_attributes": [
                {
                    "from_date": leave_details.get("start_date"),
                    "to_date": leave_details.get("end_date"),
                    "leave_type": leave_details.get("leave_type"),
                    "notifiable_profile_id": "",
                    "leave_category_id": leave_category_id,
                    "description": leave_details.get("reason", ""),
                    "reason": leave_details.get("reason"),
                    "status": "",
                    "profile_id": employee_id,
                    "profile": {"id": ""},
                    "popup1": {"opened": False},
                    "popup2": {"opened": False}
                }
            ]
        }
    }

async def apply_leave(confirmation: str, tool_context: ToolContext) -> Dict[str, Any]:
    logger.info("Processing leave application...")
    logger.debug(f"Confirmation received: {confirmation}")

    try:
        logger.info("Validating leave inputs...")
        validation_error = _validate_leave_inputs(confirmation, tool_context)
        if validation_error:
            logger.warning("Leave input validation failed.")
            return {
                "status": "fail",
                "message": "Leave validation failed. Please review the inputs and try again."
            }

        leave_details = tool_context.state.get("leave_details")
        app_name = tool_context.state.get("app_name")
        leave_category = leave_details.get("leave_category")
        leave_type = leave_details.get("leave_type")

        logger.info("Checking leave balance...")
        balance = _check_leave_balance(tool_context, leave_category, leave_type)
        if not balance:
            logger.warning("Leave balance validation failed.")
            return {
                "status": "fail",
                "message": "Insufficient leave balance. Please check your available balance before applying."
            }

        logger.info("Retrieving employee authentication and profile data...")
        auth_error, auth_data, employee_id = await _get_employee_info(tool_context, app_name)
        if auth_error:
            logger.error("Failed to retrieve employee authentication info.")
            return {
                "status": "fail",
                "message": "Authentication failed. Please log in again or contact support if the problem continues."
            }

        leave_balance = tool_context.state.get("leave_balance")
        leave_category_id = _get_leave_category_id(leave_balance, leave_category)
        if not leave_category_id:
            logger.error("Leave category ID not found.")
            return {
                "status": "fail",
                "message": "Leave category ID not found. Please try again."
            }

        logger.info("Building payload for leave request...")
        payload = _build_leave_payload(employee_id, leave_details, leave_category_id)
        apply_leave_url = f"{auth_data['origin']}/api/v1/profiles/{employee_id}"

        logger.info(f"Sending leave application request to {apply_leave_url}...")
        async with httpx.AsyncClient() as client:
            response = await client.put(apply_leave_url, headers=auth_data["headers"], json=payload)

            if response.status_code in [200, 201]:
                logger.info(f"Leave applied successfully. Status Code: {response.status_code}")
                leave_details["status"] = "submitted"
                leave_details["submitted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                tool_context.state["leave_details"] = leave_details
                return {
                    "status": "success",
                    "message": "Leave applied successfully.",
                    "response": response.json() if response.content else {}
                }
            else:
                logger.error(f"Leave application failed. Status Code: {response.status_code}, Response: {response.text}")
                return {
                    "status": "fail",
                    "message": f"Failed to apply leave. Server responded with status {response.status_code}.",
                    "details": response.text
                }

    except httpx.RequestError as e:
        logger.error(f"HTTP request error during leave application: {e}", exc_info=True)
        return {"status": "fail", "message": "Failed to apply leave."}
    except Exception as e:
        logger.error(f"Unhandled exception in apply_leave: {e}", exc_info=True)
        return {"status": "fail", "message": "An unexpected error occurred while applying for leave."}