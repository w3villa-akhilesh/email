from app.services.lifecycle_hooks import after_agent_invocation_callback_context, before_agent_invocation_callback_context, simple_after_tool_modifier, simple_before_tool_modifier
from app.services.mcp_connection import connect_to_mcp_server
from app.utils.logger import logger
from google.adk.agents.llm_agent import LlmAgent
from app.services.llm_engine import get_llm_engine
from app.services.agent_prompt_service import agent_prompt_service
from app.utils.prompt import MODE_RULES
from app.core.constants import PM_BOARD_MCP_URL, USER_PROJECT_URL
from datetime import datetime
from fastapi import HTTPException
from typing import Optional, Dict, Any
from google.genai import types
from google.adk.agents.callback_context import CallbackContext
import httpx
from app.services.redis_common_state import get_session_data
from app.services.redis_cache_service import cache_service
from app.helpers.BaseAgent import Kivo_LLMAgent
from app.tools.fetch_image_on_intent import pick_image_url_by_index
from app.utils.prompt import WHATSAPP_BUTTON_FORMATTER_PROMPT

async def fetch_user_projects(session_id:str, app_name:str, origin:str):
    """
    Method used to load project names into story agent context.
    """
    
    cache_key = f"pm_user_projects:{app_name}:{session_id}"
    try:
        cached = cache_service.redis_client.get(cache_key)
        if cached:
            try:
                import json as _json
                cached_projects = _json.loads(cached)
                if isinstance(cached_projects, list):
                    logger.info(f"PM Board projects cache hit for key={cache_key} (count={len(cached_projects)})")
                    return cached_projects
            except Exception:
                logger.debug("Cached value present but not valid JSON; ignoring and refetching.")
    except Exception as e:
        logger.debug(f"Skipping cache read due to error: {e}")

    session_data = get_session_data(session_id, app_name)
    if not session_data:
        logger.warning(f"Session data not found for session: {session_id}")
        return None

    token = session_data.get("token")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    page = 1
    total_pages = 1
    all_projects = []

    logger.debug(f"Starting project fetch from origin: {origin}")

    while page <= total_pages:
        url = f"{origin}/{USER_PROJECT_URL}?page={page}"
        logger.debug(f"Fetching projects page {page} from {url}")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                projects = data.get("projects", [])
                collection = data.get("collection", {})
                total_pages = collection.get("totalPages", 1)
                logger.debug(f"Received {len(projects)} projects on page {page}")
                project_names = [project.get("name") for project in projects]
                logger.debug(f"Extracted project names: {project_names}")
                all_projects.extend(project_names)
                page += 1
        except httpx.RequestError as e:
            logger.error(f"Network error while fetching projects: {e}")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error while fetching projects: {e.response.status_code} - {e.response.text}")
            return []

    # Cache the result for 8 hours (28800 seconds)
    try:
        import json as _json
        cache_service.redis_client.set(cache_key, _json.dumps(all_projects), ex=28800)
        logger.info(f"PM Board projects cached for key={cache_key} ttl=28800s")
    except Exception as e:
        logger.debug(f"Failed to cache PM Board projects: {e}")

    logger.info(f"Successfully fetched {len(all_projects)} total projects from PM Board.")
    return all_projects


async def save_data_in_story_context(session_id:str, company_id:str, app_name:str, date:str, callback_context: CallbackContext, origin, mode:str = None)-> Optional[types.Content]:
    agent_name=callback_context.agent_name
    logger.info(f"Entering agent- {agent_name}")

    user_projects = await fetch_user_projects(session_id, app_name, origin)

    logger.debug(f"user projects fetched as: {user_projects}")

    # Use setdefault to efficiently set state with defaults
    callback_context.state['projects'] = user_projects
    return None


async def initiate_story_agent(session_id, profile_block, company_id, app_name, origin, mode, preloaded_context=None):
    try:
        logger.debug(f"Initiating Story Creator MCP tool connection ...  mode: {mode}")
        try:
            pm_board_story_toolset = await connect_to_mcp_server(PM_BOARD_MCP_URL, session_id=session_id)
            if not pm_board_story_toolset:
                logger.warning("MCP server connection returned no tools; proceeding with empty toolset.")
                pm_board_story_toolset = []
        except Exception as mcp_error:
            logger.error(f"Failed to connect to PM Board Story MCP server: {mcp_error}", exc_info=True)
            logger.warning("Proceeding with empty toolset due to MCP connection failure.")
            pm_board_story_toolset = []
        
        logger.info("Setting up pm_board_story_agent")
        # Use user_pm_board_story_agent for user_agent context, otherwise pm_board_story_agent
        agent_name_for_llm = "user_pm_board_story_agent" if app_name == "user_agent" else "pm_board_story_agent"
        story_creator_agent_model = get_llm_engine(agent_name_for_llm, company_id, app_name=app_name, origin=origin)
        date = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
            
        async def load_story_agent_context(callback_context: CallbackContext):
            return await save_data_in_story_context(session_id, company_id, app_name, date, callback_context, origin, mode)

        # Get dynamic instructions for PM Board Story agent
        pm_board_story_agent_instructions = agent_prompt_service.get_agent_prompt(
            agent_name=agent_name_for_llm,
            company_id=company_id,
            session_id=session_id,
            profile_info=profile_block,
            preloaded_context=preloaded_context,
            mode=mode,
            projects=[],  # Will be populated by the callback context
            is_image_upload=False  # Default to False, will be updated based on actual upload
        )

        user_projects = await fetch_user_projects(session_id, app_name, origin)
        user_projects_ins = f"These are list of projects: {user_projects}, provide as order list"
        
        # Combine with MODE_RULES as before
        combined_instruction = f"{pm_board_story_agent_instructions}\n\n{MODE_RULES}\n\n{user_projects_ins} \n\n {WHATSAPP_BUTTON_FORMATTER_PROMPT}"

        story_creator_agent = Kivo_LLMAgent(
            name=agent_name_for_llm,  # Use dynamic name based on context (user_pm_board_story_agent or pm_board_story_agent)
            model=story_creator_agent_model,
            instruction=combined_instruction,
            description=agent_prompt_service.get_agent_description(agent_name_for_llm, company_id),
            output_key="story_output",
            tools=pm_board_story_toolset,
            before_agent_callback=load_story_agent_context, # check before executing agent
            after_agent_callback=after_agent_invocation_callback_context,    # check after executing agent
            before_tool_callback=simple_before_tool_modifier,
            after_tool_callback=simple_after_tool_modifier # Assign the callback
        )
        return story_creator_agent  # Return the agent here

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error in initiate_story_agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"pm_board_story_agent initialization failed: {str(e)}")
