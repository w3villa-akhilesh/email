from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.base_tool import BaseTool
from typing import Optional, Dict, Any
from google.genai import types
from google.adk.models import LlmResponse
import httpx
from app.services.redis_common_state import get_session_data
from app.utils.logger import logger
import re
import json
from app.socket.connect import manager
import asyncio
from typing import Optional, Dict, Any
from openai import OpenAI
import os 
from dotenv import load_dotenv
from pm_board_data.core.config import BASE_URL
load_dotenv()

def process_progress_and_get_clean_text(agent_name, text: str) -> tuple[Optional[str], str]:
    """
    Extracts the progress message from a <progress> tag and returns the cleaned text.

    Args:
        text: The input text possibly containing a <progress> tag.

    Returns:
        A tuple containing:
        - The extracted progress message as a string, or None if not found.
        - The text with the <progress> tag removed.
    """
    logger.debug(f"Agent {agent_name}, Processing progress and getting clean text : {text} ")
    progress_pattern = r"<progress>\s*(.*?)\s*</progress>"
    match = re.search(progress_pattern, text, re.DOTALL)
    
    if match:
        progress_message = match.group(1).strip()
        cleaned_text = re.sub(progress_pattern, "", text, flags=re.DOTALL).strip()
        return progress_message, cleaned_text
    
    return None, text


async def get_tool_progress_summary(tool_name: str, args: Dict[str, Any]) -> str:
    """
    Generates a progress message from tool arguments using OpenAI GPT-4o-mini.
    """
    try:
        prompt = (
            f"A tool named {tool_name} was invoked with the following parameters: {args}.\n\n"
            "Your task is to generate a very short, human-readable progress message.\n"
            "Do not mention:\n"
            "- The tool name\n"
            "- The words 'session', 'session ID', or 'session name' (these are strictly forbidden)\n\n"
            "The message should:\n"
            "- Be brief (one short sentence)\n"
            "- Sound like a user-facing status update\n"
            "- Be clear and natural for a non-technical reader\n"
            "- Describe what is currently happening or being fetched\n\n"
            "Examples:\n"
            "- Fetching candidate info based on skill Ruby\n"
            "- Analyzing uploaded resume for relevant skills\n\n"
            "Generate only the message. Do not include extra text, explanation, or formatting."
        )

        client = OpenAI(
            base_url=os.getenv('OPENAI_API_BASE'),  
            api_key=os.getenv('OPENAI_API_KEY')
        )

        response = client.responses.create(
            model=os.getenv("LLM_UPDATE_MODEL", "gpt-4o"),
            input=prompt
        )

        return response.output_text

    except Exception as e:
        logger.warning(f"OpenAI completion failed: {e}")
        return "Processing your request..."


async def save_data_in_context(user_id:str, session_id: str, callback_context: CallbackContext)-> Optional[types.Content]:
    agent_name=callback_context.agent_name
    logger.info(f"Entering agent: {agent_name}")
    logger.info("Loading session_id into state.")
    # Use setdefault to efficiently set state with defaults
    callback_context.state.setdefault("session_id", session_id)
    callback_context.state.setdefault("user_id", user_id)
    callback_context.state.setdefault("progress", "Planning approch")
    callback_context.state.setdefault("available_skills", "")
    
    # Use setdefault to get image upload state with default
    is_image_upload = callback_context.state.setdefault("is_image_upload", False)
    logger.info(f"Image upload state: {is_image_upload}")
    
    return None

# called inside before agent callback for loading skills before initiating iats_candidate_agent
async def fetch_and_load_available_skills(session_id:str, callback_context: CallbackContext)-> Optional[types.Content]:
    try:
        agent_name = callback_context.agent_name

        # only execute for candidate_iats_agent
        if agent_name == "candidate_iats_agent":
            logger.debug(f"Entering agent: {agent_name}.")
            session_data = get_session_data(session_id)
            token = session_data.get("token") if isinstance(session_data.get("token"), str) else None
            origin = session_data.get("origin")

            if not token:
                logger.error("Invalid or missing token in session.")
                return {"status": "error", "message": "Missing or invalid token."}

            api_url = f"{origin}/api/v1/fetch_available_skills"

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url=api_url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    },
                    timeout=15.0
                )

                response.raise_for_status()
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and isinstance(data.get("skills"), list):
                        # convert list of skills to a comma-separated string
                        skill_string = ", ".join(map(str, data["skills"]))
                        current_skills_str = callback_context.state.get("available_skills", "")
                        current_skills_list = [s.strip() for s in current_skills_str.split(",") if s.strip()]
                        logger.debug(f"Fetched skills count: {len(data['skills'])}, Current skills count: {len(current_skills_list)}")
                        # compare fetched skills with current skills
                        if len(data["skills"]) != len(current_skills_list):
                            callback_context.state["available_skills"] = skill_string
                            logger.info(f"Successfully fetched available skills, {skill_string}")
                        else:
                            logger.info("Available skills unchanged; skipping update.")
            
    except Exception as e:
        logger.error(f"Failed to fetch available skills: {e}", exc_info=True)


async def save_data_in_tool_context(session_id: str, tool_context: ToolContext)-> Optional[types.Content]:
    tool_context.state["session_id"] = session_id
    return None

async def before_agent_invocation_callback_context(callback_context: CallbackContext) -> Optional[types.Content]:
    agent_name = callback_context.agent_name
    logger.debug(f"Entering agent: {agent_name}.")


async def after_agent_invocation_callback_context(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Logs agent completion. The response modification is now handled by after_model_response_callback.
    """
    agent_name = callback_context.agent_name
    current_state = callback_context.state.to_dict()
    logger.debug(f"Exiting agent: {agent_name} with state: {json.dumps(current_state, indent=4)}")
    return None


async def after_model_response_callback(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """
    Intercepts model responses to extract progress updates and clean the final output.
    This should be registered in the agent's 'after_model_callback' parameter.
    """
    try:
        if not (llm_response.content and llm_response.content.parts):
            return None

        if llm_response.error_message:
            logger.warning(f"[Callback] Inspected response: Contains error '{llm_response.error_message}'. No modification.")
            return None
        
        part = llm_response.content.parts[0]
        # If the response is a function call, we should not process it here.
        # Return None to allow the function call to be handled by the agent.
        if part.function_call:
            return None

        source_text = part.text
        # The text can be None if the response is a function call, so we need to handle this.
        if not isinstance(source_text, str):
            return None

        agent_name = callback_context.agent_name
        session_id = callback_context.state.get("session_id")

        if not session_id:
            logger.warning("Could not find session_id in state for after_model_response_callback.")
            return None

        # latest_progress, modified_text = process_progress_and_get_clean_text(agent_name, source_text)

        # if latest_progress:
        #     logger.debug(f"Extracted progress from {agent_name}: '{latest_progress}'")
            
        #     if agent_name in ["job_profile_agent", "candidate_iats_agent", "custom_matching_agent", "iats_agent"]:
        #         try:
        #             await manager.broadcast_json_to_session(session_id, {
        #                 "type": "status_update",
        #                 "session_id": session_id,
        #                 "message": latest_progress
        #             })
        #         except RuntimeError as e:
        #             logger.error(f"Broadcast failed for session {session_id}: {e}")
            
        #     logger.debug("Stripped progress tag from model response.")
        #     modified_parts = [types.Part(text=modified_text)]
        #     return LlmResponse(
        #         content=types.Content(role="model", parts=modified_parts),
        #         grounding_metadata=llm_response.grounding_metadata
        #     )
        # else:
        #     logger.debug("No progress tag found in model response.")

        return None
    except Exception as e:
        logger.error(f"Error processing LLM response: {e}")
        logger.error(f"LLM Response that caused error: {llm_response}")
        return None


async def simple_before_tool_modifier(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext
) -> Optional[Dict]:
    """
    Logs entry into tool execution, generates a dynamic progress message,
    and emits it via WebSocket to the frontend.
    """
    agent_name = tool_context.agent_name
    tool_name = tool.name
    session_id = tool_context.state["session_id"]

    logger.info(f"Tool Invoked by agent '{tool_name}' with args: {args}")

    # if agent_name == "job_profile_agent" or agent_name == "candidate_iats_agent":
    #     latest_progress = await get_tool_progress_summary(tool_name, args)
    #     await manager.broadcast_json_to_session(session_id, {
    #         "type": "status_update",
    #         "session_id": session_id,
    #         "message": latest_progress
    #     })

    return None

def simple_after_tool_modifier(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext, tool_response: Dict
) -> Optional[Dict]:
    """
    Logs completion of tool execution.
    """
    agent_name = tool_context.agent_name
    tool_name = tool.name
    invocation_id = tool_context.invocation_id
    session_id = tool_context._invocation_context.session.id
    type = "tool"
    status = "after"

    # logger.info(f"Tool call completed: {tool_name} in agent: {agent_name} with args:{args} and response: {tool_response}")
    # save_output_to_db(
    #     invocation_id=invocation_id,
    #     session_id=session_id,
    #     response=tool_response,
    #     agent_name=agent_name,
    #     type=type,
    #     tool_name=tool_name,
    #     number_of_calls=1,
    #     status=status
    # )
    return None
