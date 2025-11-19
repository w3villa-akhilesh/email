import json
from fastapi import HTTPException, Depends, status, FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.services.authenticate_agent import get_mode_from_request, get_origin_from_request
from app.utils.logger import logger
from app.services.email_notifier import send_exception_email
# rexnord related imports
from rexnord.models.schema import RexnordTriageAgentRequest
from rexnord.helpers.rexnord_triage_agent import initiate_rexnord_agent

# Endpoint to invoke rexnord agent whch is responsible to route queries to respective sub-agents like dealer, products of rexnord, faq etc agents.

# curl --location 'http://127.0.0.1:8080/invoke-rexnord-agent' \
# --header 'Content-Type: application/json' \
# --header 'origin: https://crm.kivo.ai/' \
# --header 'X-Request-Mode: crm' \
# --data-raw '{
#   "query":"what products you have?",
#   "query_id": "rexnord@gmail.com",
#   "profile_info": {
#     "name": "John Doe",
#     "number": "+91-9876543210",
#     "company_id": "1"
#   }
# }'

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/invoke-rexnord-agent")
async def invoke_rexnord_triage_agent(
    request_data: RexnordTriageAgentRequest,
    origin: str = Depends(get_origin_from_request),
    mode: str = Depends(get_mode_from_request)
):
    """
    Endpoint to invoke rexnord agent whch is responsible to route queries to respective sub-agents 
    like dealer, products of rexnord, faq etc agents.

    """
    # Initialize variables that might be needed in exception handling
    profile_info = None
    company_id = None
    
    try:
        logger.info(f"[Rexnord Agent] from headers origin is {origin} and mode {mode}")

        # Extract token from Authorization header
        # token = credentials.credentials
        # Extract data from request body
        query = request_data.query
        user_id = request_data.query_id
        session_id = f"session_{user_id}"
        parent_origin = ""
        app_name = "rexnord_agent"
        # profile_info may come as a JSON string; normalize to dict
        raw_profile = request_data.profile_info
        
        if isinstance(raw_profile, str):
            try:
                profile_info = json.loads(raw_profile)
            except Exception:
                logger.error("profile_info is not valid JSON string; defaulting to empty dict")
                profile_info = {}
        elif isinstance(raw_profile, dict):
            profile_info = raw_profile
        else:
            # Attempt to coerce pydantic model if provided
            try:
                profile_info = raw_profile.model_dump()
            except Exception:
                profile_info = {}

        # logger.info(f"Received origin: {origin}, \n query_id: {query_id}, \n token: {token}")

        # Normalize origin for robust comparison (trim spaces, lower, drop trailing slash)
        origin_norm = origin.strip().lower().rstrip('/')
        allowed_origins = ['https://crm.kivo.ai/', 'https://staging-crm.kivo.ai/']
        allowed_norm = [o.strip().lower().rstrip('/') for o in allowed_origins]

        if origin_norm not in allowed_norm:
            logger.error(f"Provided origin {origin} not in {allowed_origins}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "status": "error",
                    "message": "Provided origin does not have access. Please contact the administrator."
                }
            )

       
        # if not token or not user_id:
        #     raise HTTPException(
        #         status_code=status.HTTP_400_BAD_REQUEST,
        #         detail="Missing required token or number"
        #     )

        if not profile_info:
            logger.error(f"Profile information not found for query_id: {user_id}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "status": "error",
                    "message": "You do not have access. Please contact the administrator."
                }
            )
        
        # Extract company_id for error tracking
        company_id = profile_info.get("company_id")

        # Initiate rexnord agent 

        rexnord_agent_result = await initiate_rexnord_agent(query, user_id=user_id, session_id=session_id, profile_info=profile_info, origin=origin, parent_origin=parent_origin, mode=mode, token="", app_name=app_name)
                
        # Safely unpack the result
        if isinstance(rexnord_agent_result, tuple) and len(rexnord_agent_result) == 2:
            response, event_id = rexnord_agent_result
        else:
            logger.error(f"Unexpected return format from rexnord triage agent: {rexnord_agent_result}")
            raise HTTPException(status_code=500, detail="Rexnord Agent returned unexpected response format")

            # Process the request (this is a placeholder for actual processing logic

        return {
            "status": "success",
            "type": "final_response",
            "message": f"Rexnord Agent invoked",
            "query": query,
            "response": response,
            "session_id": session_id,
            "event_id": event_id,
        }

    except Exception as e:
        logger.error(f"Error invoking Rexnord Agent: {e}", exc_info=True)
        send_exception_email(e, f"Error invoking Rexnord Agent: {str(e)} | Session ID: {session_id} | Query: {query} | Origin: {origin} | Company ID: {company_id}", session_id=session_id, origin=origin, company_id=company_id)
        raise HTTPException(status_code=500, detail="Failed to invoke Rexnord Agent")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("rexnord_main:app", host="0.0.0.0", port=8081, reload=False)
