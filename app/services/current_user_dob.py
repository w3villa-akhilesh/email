import httpx
from app.utils.logger import logger
from app.services.redis_common_state import get_session_data

async def get_current_profile_dob(token: str, origin: str) -> dict:
    """
    This tool provides the date of birth of the logged-in user.
    """

    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    CURRENT_PROFILE_URL=f"{origin}api/v1/profiles/current_profile"
    logger.debug(f"[CurrentProfileDobTool] Fetching data from HRMS URL: {CURRENT_PROFILE_URL}, token: {token}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(CURRENT_PROFILE_URL, headers=headers)
            response.raise_for_status()
            data = response.json()
            if not data:
                logger.error("[CurrentProfileDobTool] No data found in response")
                return {"error": "No profile data found."}
            logger.debug(f"---- dob data {data}")
            response_data={
                "dob": data.get("dob")
                }            
            return response_data
    except httpx.RequestError as e:
        logger.error(f"[CurrentProfileDobTool] Request error: {e}")
        return {"error": "Failed to fetch dob from HRMS."}