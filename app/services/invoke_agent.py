from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from app.services.current_user_info import get_current_profile
from app.services.redis_common_state import save_session_data, get_session_data
from app.utils.logger import logger
from app.services.email_notifier import send_exception_email
import json
from pm_board_data.core.config import BASE_URL
from app.services.state_session_manager import create_user_session, update_user_session_history, list_user_sessions, get_user_session_details
from app.services.my_sql_client import get_db
from sqlalchemy.orm import Session
from app.services.state_session_manager import check_existing_session
from app.core.exceptions import LLMKeyNotSetException

async def invoke_agent(
    request_data,
    credentials,
    agent_name: str,
    initiate_agent_func: callable,
    session_id_prefix: str = ""
):
    try:
        # Extract essential data from request and credentials
        token = credentials.credentials
        query = getattr(request_data, 'query', None)
        origin = getattr(request_data, 'origin', None)
        user_id = getattr(request_data, 'user_id', None)
        parent_origin = getattr(request_data, 'parent_origin', None)
        session_id = getattr(request_data, 'session_id', None)
        image_url = getattr(request_data,"image_url",None)
        extracted_info_from_image = getattr(request_data,"extracted_info_from_image",None)
        app_name = getattr(request_data, 'app_name', None)
        company_id = None
        
        if origin:
            origin = origin.lower()
        if not origin:
            raise HTTPException(status_code=302, detail="Could not find origin.")

        logger.info(f"origin: {origin} parent_origin: {parent_origin}, session_id: {session_id}")

        if not token or not user_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Missing token or user_id")

        # Fetch user profile
        profile_info = await get_current_profile(token, origin)
        if not profile_info:
            logger.error(f"No profile for user_id: {user_id}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"status": "error", "message": "Access denied. Contact administrator."}
            )
        company_id = profile_info.get('company_id')
        if not company_id:
            logger.error(f"Company ID not found in profile, cannot load llm keys.")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"status": "error", "message": "Cannot load llm keys. Contact administrator."}
            )
        
        # Load or initialize session data
        session_data = get_session_data(session_id) or {"token": token, "history": "[]", "origin": origin}

        session_data["token"] = token
        session_data["origin"] = origin
        session_data["company_id"] = company_id 
        
        # Save user's phone number from profile_info for calling agent
        if profile_info and profile_info.get("phone_number"):
            session_data["user_phone_number"] = profile_info["phone_number"]
            logger.debug(f"Saved user phone number to session: {profile_info['phone_number']}")

        # redis common state for token availability mcp tools
        save_session_data(session_id, session_data)
        db: Session = next(get_db())

        if not check_existing_session(db, session_id):
            logger.info(f"New Db Session {session_id}.")
            create_user_session(db, user_id, session_id, app_name)
        else:
            logger.info(f"Db Session {session_id} already exists, skipping creation.")
        extracted_info=None
        if image_url:
            logger.debug("checking for image url")
            extracted_info_from_image = getattr(request_data,"extracted_info_from_image",None)
            if extracted_info_from_image:
                extracted_info = extracted_info_from_image
            
        # Execute agent-specific logic
        response = await initiate_agent_func(
            query, user_id=user_id, session_id=session_id, chat=query,
            profile_info=profile_info, origin=origin, parent_origin=parent_origin, company_id=company_id, extracted_info=extracted_info
        )

        # converted str to python dict using json.loads
        response_dict = json.loads(response)
        
        # assistant_reply should be last 3-4 words of full_response.
        await update_user_session_history(db, session_id=session_id, user_query=query, assistant_reply=response, event_id=response_dict.get("event_id", None), origin=origin, company_id=company_id)       

        return {
            "status": "success",
            "type": "final_response",
            "message": f"{agent_name} Agent invoked",
            "query": query,
            "response": response_dict,
            "session_id": session_id,
        }

    except LLMKeyNotSetException:
        # Re-raise LLMKeyNotSetException without modification to preserve its context
        raise
    except Exception as e:
        # Handle errors and notify
        logger.error(f"Error invoking {agent_name}: {e}", exc_info=True)
        send_exception_email(e, f"Error invoking {agent_name}: {str(e)} | Session ID: {session_id} | Query: {query} | Origin: {origin} | Company ID: {company_id}", session_id=session_id, origin=origin, company_id=company_id)
        raise HTTPException(status_code=500, detail=f"Failed to invoke {agent_name} Agent") 