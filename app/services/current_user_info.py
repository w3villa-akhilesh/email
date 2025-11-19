import httpx
from app.utils.logger import logger
from app.services.redis_common_state import get_session_data

async def get_current_profile(token: str, origin: str) -> dict:
    """
    This tool provides the information of the logged-in user, including their name, email, and other profile details.
    """
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    CURRENT_PROFILE_URL=f"{origin}/api/v1/companies/current_profile"
    logger.debug(f"[CurrentProfileTool] Fetching data from HRMS URL: {CURRENT_PROFILE_URL}, token: {token}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(CURRENT_PROFILE_URL, headers=headers)
            response.raise_for_status()
            data = response.json().get("current_profile", {})
            if not data:
                logger.error("[CurrentProfileTool] No data found in response")
                return {"error": "No profile data found."}

            response_data={
                "name": data.get("full_name"),
                "email": data.get("email"),
                "designation": data.get("designation"),
                "company_name": data.get("company_name"),
                "phone_number": data.get("phone"),
                "company_id": data.get("current_company_id"),
                "is_admin": data.get("is_admin")
                }            
            
            
            return response_data
    except httpx.RequestError as e:
        logger.error(f"[CurrentProfileTool] Request error: {e}")
        return {"error": "Failed to fetch data from HRMS."}
    
    
