from fastapi.security import APIKeyHeader
from app.utils.logger import logger
from fastapi import HTTPException, Depends, Request
import os
from dotenv import load_dotenv
from pm_board_data.core.config import KIVO_API_BASE_URL
load_dotenv()

# used to authenticate key to invoke agent 
invoke_kivo_agent_api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

async def authenticate_invoke_kivo_agent(invoke_kivo_agent_key: str = Depends(invoke_kivo_agent_api_key_header)):

    expected_api_key=os.getenv("INVOKE_KIVO_AGENT_KEY")
    logger.debug(f"auth_api_key: {invoke_kivo_agent_key} and env_key: {os.getenv('INVOKE_KIVO_AGENT_KEY')}")
    
    if invoke_kivo_agent_key != expected_api_key:
        raise HTTPException(status_code=401, detail="Unauthorized please provide 'INVOKE_KIVO_AGENT_KEY'")
    logger.info(f"API_KEY {invoke_kivo_agent_key} is valid")


async def get_base_url_from_request(request: Request) -> str:
    is_production = os.getenv('PRODUCTION_MODE', 'false').lower() == 'true'

    if not is_production:
        logger.info(f"Not in production mode, using KIVO_API_BASE_URL: {KIVO_API_BASE_URL}")
        return KIVO_API_BASE_URL
        
    # Use forwarded headers if available, falling back to the direct request info
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host"))

    if not host:
        logger.error("Could not determine host from request headers.")
        raise HTTPException(status_code=400, detail="Could not determine host from request headers")

    base_url = f"{scheme}://{host}"
    
    logger.info(f"In production mode, using base_url from request: {base_url}")
    return base_url

async def get_origin_from_request(request: Request) -> str:
    origin = request.headers.get("origin")
    if not origin:
        origin = request.headers.get("X-Origin-Service") or KIVO_API_BASE_URL
    return origin

async def  get_mode_from_request(request: Request) -> str:
    mode = request.headers.get("X-Request-Mode")
    if not mode:
        mode = "web"
    return mode
