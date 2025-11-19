import httpx
from app.utils.logger import logger
from app.services.redis_common_state import get_session_data, save_session_data
import os
import json
from fastapi import HTTPException

def get_crm_profile_block(profile_info):
    """
    Creates a personalized profile block for CRM users based on their contact information.
    """
    user_email = profile_info.get('email') if profile_info else None
    user_name = profile_info.get('name', 'Unknown User')
    phone_number = profile_info.get('phone_number', '')
    company_name = profile_info.get('company_name', '')
    city = profile_info.get('city', '')
    country = profile_info.get('country', '')
    description = profile_info.get('description', '')
    
    # Create personalized profile block
    profile_block = f"""
            **Answer to query like "who i am" ?**:
            In my CRM I found that your name is {user_name}. 
            Contact Details: Phone: {phone_number}, Email: {user_email}
            {f"Company: {company_name}" if company_name else ""}
            {f"Location: {city}, {country}" if city or country else ""}
            {f"Description: {description}" if description else ""}
            
            Use this information to personalize your answers. Respond accurately when asked about the user's identity.
            """
    
    return profile_block, user_email

async def get_crm_current_profile_for_faq(session_id: str) -> dict:
    """
    This tool provides the information of the logged-in user from CRM API, including their name, email, and other profile details.
    Uses session_id as phone number to search for contact in CRM.
    """
    logger.debug(f" Initialized CRM current profile tool with Session ID: {session_id}")
    # Extract phone number from session_id (assuming session_id contains phone number)
    phone_number = session_id
    
    # CRM API credentials from environment variables
    api_access_token = os.getenv("CRM_API_ACCESS_TOKEN")
    account_id = os.getenv("CRM_ACCOUNT_ID", "3")  # Default account ID
    
    if not api_access_token:
        error_msg = "Missing CRM API access token in environment variables"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    headers = {
        "api_access_token": api_access_token,
        "Content-Type": "application/json"
    }
    
    # Construct CRM API URL with phone number search
    CRM_PROFILE_URL = f"https://crm.kivo.ai/api/v1/accounts/{account_id}/contacts/search"
    params = {
        "include_contact_inboxes": "false",
        "page": "1",
        "sort": "-created_at",
        "q": phone_number
    }
    
    logger.debug(f"Fetching data from CRM URL: {CRM_PROFILE_URL}, phone: {phone_number}")

    # Retry mechanism: maximum 2 retries (total 3 attempts)
    max_retries = 2
    last_exception = None
    
    for attempt in range(max_retries + 1):  # 0, 1, 2 (total 3 attempts)
        try:
            if attempt > 0:
                logger.warning(f"Retrying CRM profile fetch (attempt {attempt + 1}/{max_retries + 1}) for session: {session_id}")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(CRM_PROFILE_URL, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                
                # Extract contact information from response
                payload = data.get("payload", [])
                if not payload:
                    error_msg = "No contact found for phone number"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                # Get the first contact (most recent)
                contact = payload[0]
                
                response_data = {
                    "name": contact.get("name", "Unknown User"),
                    "email": contact.get("email", ""),
                    "phone_number": contact.get("phone_number", phone_number),
                    "id": contact.get("id"),
                    "availability_status": contact.get("availability_status", "offline"),
                    "created_at": contact.get("created_at"),
                    "conversations_count": contact.get("conversations_count", 0),
                    "company_name": contact.get("additional_attributes", {}).get("company_name", ""),
                    "city": contact.get("additional_attributes", {}).get("city", ""),
                    "country": contact.get("additional_attributes", {}).get("country", ""),
                    "description": contact.get("additional_attributes", {}).get("description", ""),
                    "social_profiles": contact.get("additional_attributes", {}).get("social_profiles", {}),
                    "custom_attributes": contact.get("custom_attributes", {})
                }
                
                # Generate profile block using the combined function
                profile_block, user_email = get_crm_profile_block(response_data)
                response_data["profile_block"] = profile_block
                
                # Save CRM user profile data to Redis session data
                crm_user_id = response_data.get("id")
                if crm_user_id:
                    session_data = get_session_data(session_id) or {}
                    # Save user profile data as JSON string
                    user_profile_data = {
                        "email": response_data.get("email"),
                        "id": response_data.get("id"),
                        "name": response_data.get("name"),
                        "phone_number": response_data.get("phone_number")
                    }
                    session_data["user_profile"] = json.dumps(user_profile_data)
                    session_data["crm_user_id"] = str(crm_user_id)
                    save_session_data(session_id, session_data)
                    logger.debug(f"Saved CRM user profile data to session {session_id}")
                
                # Success! Log if this was a retry and return the data
                if attempt > 0:
                    logger.info(f"CRM profile fetch succeeded on attempt {attempt + 1} for session: {session_id}")
                logger.debug(f"Data fetched successfully: {response_data}")
                return response_data
                
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                # Not the last attempt, so we'll retry
                logger.warning(f"CRM profile fetch failed on attempt {attempt + 1}/{max_retries + 1} for session: {session_id}. Error: {e}")
            else:
                # Last attempt failed, log error and re-raise
                logger.error(f"All {max_retries + 1} attempts failed for CRM profile fetch. Session: {session_id}. Final error: {e}", exc_info=True)
                
    # If we reach here, all retries failed - raise the last exception
    raise last_exception

async def get_crm_current_profile(token, origin, account_id, session_id=None) -> dict:
    """
    This tool provides the information of the logged-in user from CRM API, including their name, email, and other profile details.
    Fetches the current user's profile information using the provided access token.
    """
    
    # CRM API credentials from environment variables
    api_access_token = token
    
    if not api_access_token:
        error_msg = "Missing CRM API access token in environment variables"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    headers = {
        "api_access_token": api_access_token,
        "Content-Type": "application/json"
    }
    
    # Construct CRM API URL with phone number search
    CRM_PROFILE_URL = f"{origin}/api/v1/profile"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(CRM_PROFILE_URL, headers=headers) 

            # Check if response is successful before parsing JSON
            response.raise_for_status()
            
            # Check if response has content before parsing JSON
            if not response.text.strip():
                error_msg = "Empty response from CRM API"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            try:
                data = response.json()
                logger.debug(f"Parsed JSON response: {data}")
            except json.JSONDecodeError as json_error:
                error_msg = f"Invalid JSON response from CRM API: {json_error}"
                logger.error(f"{error_msg}. Response content: {response.text}")
                raise ValueError(error_msg)
            
            # Extract user information from direct response
            # The API returns user profile information directly, not in a payload array
            if not data.get("id"):
                error_msg = "No user profile found in response"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Get account information from accounts array
            accounts = data.get("accounts", [])
            company_name = ""
            if accounts:
                company_name = accounts[0].get("name", "")
            
            response_data = {
                "name": data.get("name", "Unknown User"),
                "email": data.get("email", ""),
                "company_id": data.get("account_id"), # account_id is the company_id is works in CRM
                "id": data.get("id"),
                "company_name": company_name,
                "description": data.get("message_signature", ""),  # Using message signature as description
                "account_id": data.get("account_id")
            }
            
            # Generate profile block using the combined function
            profile_block, user_email = get_crm_profile_block(response_data)
            response_data["profile_block"] = profile_block
            
            # Save CRM user profile data to Redis session data
            crm_user_id = response_data.get("id")
            if crm_user_id and session_id:
                session_data = get_session_data(session_id) or {}
                # Save user profile data as JSON string
                user_profile_data = {
                    "email": response_data.get("email"),
                    "id": response_data.get("id"),
                    "name": response_data.get("name"),
                    "phone_number": response_data.get("phone_number")
                }
                session_data["user_profile"] = json.dumps(user_profile_data)
                session_data["crm_user_id"] = str(crm_user_id)
                save_session_data(session_id, session_data)
                logger.debug(f"Saved CRM user profile data to session {session_id}")
            elif crm_user_id and not session_id:
                logger.warning("CRM user profile fetched but no session_id provided for Redis storage")
            
            logger.debug(f"Data fetched successfully: {response_data}")
            return response_data
            
    except Exception as e:
        logger.error(f"Error fetching CRM profile: {e}", exc_info=True)
        raise


# def get_user_profile_from_redis(session_id: str) -> dict:
#     """
#     Retrieve user profile data from Redis session.
#     Returns the user profile dictionary or empty dict if not found.
    
#     Example usage:
#         user_profile = get_user_profile_from_redis("+919336062297")
#         # Returns: {"email": "user@example.com", "id": 227169, "name": "!! प्रणव गुप्ता !!", "phone_number": "+919336062297"}
#     """
#     try:
#         session_data = get_session_data(session_id)
#         if session_data and "user_profile" in session_data:
#             user_profile = json.loads(session_data["user_profile"])
#             logger.debug(f"[GetUserProfile] Retrieved user profile from Redis for session {session_id}")
#             return user_profile
#         else:
#             logger.debug(f"[GetUserProfile] No user profile found in Redis for session {session_id}")
#             return {}
#     except (json.JSONDecodeError, KeyError) as e:
#         logger.error(f"[GetUserProfile] Error retrieving user profile from Redis: {e}")
#         return {}
