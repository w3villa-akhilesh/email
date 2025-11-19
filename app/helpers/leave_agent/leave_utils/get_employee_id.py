from app.utils.logger import logger
import httpx
from typing import Dict, Any

async def get_employee_id(origin_url: str, headers: Dict[str, str]) -> Dict[str, Any]:
    """
    Helper function to fetch employee ID from the API.
    
    Returns:
        dict: Contains employee_id or error information
    """
    current_profile_url = f"{origin_url}/api/v1/companies/current_profile"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(current_profile_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            employee_id = data.get("current_profile", {}).get("id")
            
            if not employee_id:
                logger.debug("Employee ID not found in profile data")
                return {"error": "Employee ID not found in profile data."}
            
            return {"employee_id": employee_id}
            
    except httpx.RequestError as e:
        logger.error(f"Error fetching employee ID: {e}")
        logger.debug("Failed to fetch employee ID due to request error")
        return {"error": "Failed to fetch employee ID."}