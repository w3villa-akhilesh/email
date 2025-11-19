from typing import Dict, Any, Optional
from app.utils.logger import logger
import httpx

FULL_DAY_LEAVE = "Full Day Leave"
HALF_DAY_LEAVE = "Half Day Leave"
DEFAULT_PAGE_NUMBER = 1

def _process_leave_record(leave: dict, start_date: str) -> Optional[dict]:
    """Process a single leave record and return leave info if valid."""
    leave_from_date = leave.get("from_date")
    leave_type = leave.get("leave_type")

    if leave_from_date != start_date or not leave_type:
        return None

    return {
        "category": leave.get("leave_category_name", "Unknown"),
        "type": leave_type,
        "reason": leave.get("reason", "No reason provided"),
        "status": leave.get("status", "Pending") or "Pending"
    }

async def check_existing_leave_on_date(start_date: str, auth_data: Dict[str, Any], applied_leave_type: str) -> Dict[str, Any]:
    """
    Helper function to check if any leave is already applied on the given date.
    
    Args:
        start_date (str): Date to check in YYYY-MM-DD format
        auth_data (dict): Authentication data containing headers, origin, etc.
    
    Returns:
        dict: Contains validation result and existing leave details if found
    """
    try:
        # API endpoint to check existing leaves
        leaves_url = f"{auth_data['origin']}/api/v1/companies/list_all_profile_leaves"
        params = {
            "status": "",
            "from_date": start_date,
            "to_date": start_date,
            "page": DEFAULT_PAGE_NUMBER
        }
        
        
        async with httpx.AsyncClient() as client:
            response = await client.get(leaves_url, headers=auth_data["headers"], params=params)
           
            response.raise_for_status()

            data = response.json()
            if not isinstance(data, list):
                logger.error(f"Expected list from leave API, got: {data}")
                return {"has_existing_leave": False, "error": "Invalid response from leave API."}

            leaves = data
            
            if leaves:
                # Found existing leaves on this date
                existing_leave_details = []
                full_day_leave_count = 0
                half_day_leave_count = 0
                for leave in leaves:
                    processed = _process_leave_record(leave, start_date)
                    if not processed:
                        continue

                    if processed["type"] == FULL_DAY_LEAVE:
                        full_day_leave_count += 1
                    elif processed["type"] == HALF_DAY_LEAVE:
                        half_day_leave_count += 1

                    existing_leave_details.append(processed)
                logger.debug(f"Existing leave details: {existing_leave_details}")
                logger.debug(f"Total leaves: {len(leaves)}")
                logger.debug(f"Total existing_leave_details: {existing_leave_details}")

                logger.debug(f"Final Leave count, full: {full_day_leave_count} half: {half_day_leave_count}")
                if full_day_leave_count > 0 or half_day_leave_count > 1:
                    return {
                        "has_existing_leave": True,
                        "existing_leaves": existing_leave_details,
                        "total_leaves": len(leaves)
                    }
                else: 
                    if applied_leave_type == HALF_DAY_LEAVE:
                        logger.info("Only one half day leave found, returning false")
                        return {"has_existing_leave": False}
            
            return {"has_existing_leave": False}
            
    except httpx.RequestError as e:
        logger.error(f"Error checking existing leaves: {e}")
        logger.exception("Detailed traceback for leave check failure")
        return {"has_existing_leave": False, "error": "Unable to verify existing leaves. Please try again."}
    except Exception as e:
        logger.error(f"Unexpected error checking existing leaves: {e}")
        logger.exception("Detailed traceback for leave check failure")
        return {"has_existing_leave": False, "error": "Unable to verify existing leaves. Please try again."}



def check_leave_balance_availability(
    leave_balance: list, 
    leave_category: str, 
    leave_type: str
) -> Dict[str, Any]:
    """
    Check if applying for leave would result in negative balance.
    
    Example: User has 0.5 days of Sick Leave, requests Full Day Leave (1 day)
    Result: 0.5 - 1.0 = -0.5 (negative balance) → Block application, contact HR
    
    Args:
        leave_balance (list): List of leave balance data with id, name, balance
        leave_category (str): Category of leave being applied for
        leave_type (str): Type of leave (Full Day Leave or Half Day Leave)
        
    Returns:
        dict: Status and message about balance availability
        - status: "sufficient", "insufficient_balance", or "error"
        - message: User-friendly message about balance status
    """
    try:
        # Calculate leave days requested
        leave_days_requested = 1.0 if leave_type == FULL_DAY_LEAVE else 0.5
        
        # Find the specific leave category balance
        current_balance = None
        for leave in leave_balance:
            if leave.get("name", "").lower() == leave_category.lower():
                current_balance = float(leave.get("balance", 0))
                print("current_balance:",current_balance)
                break
        
        if current_balance is None:
            logger.debug(f"Leave category '{leave_category}' not found in balance data")
            return {
                "status": "error",
                "message": f"Leave type '{leave_category}' not available. Please select from valid options."
            }
        
        # Check if balance would go negative
        remaining_balance = current_balance - leave_days_requested
        
        if remaining_balance < 0:
            logger.debug(f"Insufficient leave balance: current={current_balance}, requested={leave_days_requested}, remaining={remaining_balance}")
            return {
                "status": "insufficient_balance",
                "message": f"Insufficient balance. Available: {current_balance} days, Requested: {leave_days_requested} days. Please contact HR.",
                "current_balance": current_balance,
                "requested_days": leave_days_requested,
                "remaining_balance": remaining_balance
            }
        
        return {
            "status": "sufficient",
            "message": f"Balance confirmed. Current: {current_balance}, Requesting: {leave_days_requested}, Remaining: {remaining_balance} days",
            "current_balance": current_balance,
            "requested_days": leave_days_requested,
            "remaining_balance": remaining_balance
        }
        
    except Exception as e:
        logger.error(f"Error checking leave balance: {e}", exc_info=True)
        return {
            "status": "error",
            "message": "Unable to verify balance. try again."
        }