from fastapi import HTTPException
from app.models.schema import IATSResponse
from app.services.iats_lifecycle_hooks import after_agent_invocation_callback_context, before_agent_invocation_callback_context, save_data_in_context, after_model_response_callback
from app.services.my_sql_client import create_db_url
from app.utils.final_logger import get_final_agent_response
from app.utils.logger import logger
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.genai import types
from app.services.llm_engine import get_llm_engine
import uuid
from app.utils.prompt import IATS_AGENT_PROMPT, OUTPUT_FORMATTER_AGENT_PROMPT, IATS_GLOBAL_INSTRUCTIONS
from app.services.agent_prompt_service import agent_prompt_service
import json
import os
from google.adk.sessions import DatabaseSessionService
from pm_board_data.core.config import BASE_URL, KIVO_API_BASE_URL
from datetime import datetime
import time
from app.services.profile_block import get_my_profile_block
from google.adk.tools.agent_tool import AgentTool
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from typing import Optional, Dict, Any
from google.adk.models import LlmResponse
import copy
from google.adk.events import Event, EventActions
from app.utils.memory_utils import memorize
from app.core.exceptions import LLMKeyNotSetException
from app.utils.error_reporter import report_agent_initialization_errors
from app.services.agent_registry import AgentRegistryService

# Function to check if the output is in json format
def after_model_response_callback_for_json_check(
    callback_context: CallbackContext,
    llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """
    Checks if the model output is a valid JSON.
    If not, it logs the issue and returns a fallback JSON response.
    """
    if not llm_response.content or not llm_response.content.parts:
        return None

    if llm_response.error_message:
        logger.warning(f"[Callback] Inspected response: Contains error '{llm_response.error_message}'. No modification.")
        return None

    raw_response = llm_response.content.parts[0].text
    try:
        json.loads(raw_response)
        logger.info(f"JSON check passed for agent '{callback_context.agent_name}'.")
        return None
    except (json.JSONDecodeError, TypeError):
        agent_name = callback_context.agent_name
        logger.warning(
            f"Output from model for agent '{agent_name}' is not valid JSON. "
            f"Original response: '{raw_response and raw_response[:200]}...'"
        )

        failure_response_dict = {
          "status": "Failure", 
          "response_type": "text",
          "full_response": "Appologies, I am unable to process your request, please try again"
        }
        failure_response_json = json.dumps(failure_response_dict, indent=2)

        modified_parts = [types.Part(text=failure_response_json)]
        
        new_response = LlmResponse(
             content=types.Content(role="model", parts=modified_parts),
             grounding_metadata=llm_response.grounding_metadata
             )
        
        logger.info(f"Returning fallback JSON response for agent '{agent_name}'.")
        return new_response


# Function to initiate the iats agent with safe to run sub-agents.
async def safe_run_agent_as_tools(agent_names, user_email=None, origin=None, session_id=None, company_id=None, app_name=None):
    safe_run_agents_as_tools = []
    
    for agent_name in agent_names:
        try:
            # Prepare kwargs based on agent requirements
            kwargs = {
                "session_id": session_id,
                "company_id": company_id,
                "app_name": app_name,
                "origin": origin
            }
            
            # Add common parameters that agents might need
            kwargs.update({
                "user_email": user_email
            })
            
            logger.info(f"Creating IATS sub-agent tool for --> {agent_name} with parameters: {kwargs}")
            # Create agent instance dynamically using registry
            agent_instance = await AgentRegistryService.create_agent_instance(agent_name, **kwargs)
            
            if agent_instance:
                safe_run_agents_as_tools.append(AgentTool(agent=agent_instance))
                logger.info(f"Successfully initialized IATS sub-agent tool: {agent_name}")
            
        except Exception as e:
            logger.error(f"Error initializing {agent_name}: {e}", exc_info=False)
    
    return safe_run_agents_as_tools

async def safe_run_agents(agent_names, user_email=None, origin=None, session_id=None, company_id=None, app_name=None):
    safe_run_agents = []
    errors = []
    
    for agent_name in agent_names:
        try:
            # Prepare kwargs based on agent requirements
            kwargs = {
                "session_id": session_id,
                "company_id": company_id,
                "app_name": app_name,
                "origin": origin
            }
            
            # Add common parameters that agents might need
            kwargs.update({
                "user_email": user_email
            })
            
            logger.info(f"Creating IATS sub-agent instance for --> {agent_name} with parameters: {kwargs}")
            # Create agent instance dynamically
            agent_instance = await AgentRegistryService.create_agent_instance(agent_name, **kwargs)
            
            if agent_instance:
                safe_run_agents.append(agent_instance)
                logger.info(f"Successfully initialized IATS sub-agent: {agent_name}")
            
        except Exception as e:
            logger.error(f"Error initializing {agent_name}: {str(e)}", exc_info=True)
            errors.append({"agent": agent_name, "error": str(e)})
            continue
    
    if errors:
        report_agent_initialization_errors(
            errors=errors,
            session_id=session_id,
            origin=origin,
            company_id=company_id,
            context="safe_run_agents of Iats agent"
        )

    return safe_run_agents

async def initialize_default_job_state(
    app_name: str,
    user_id: str,
    session_id: str,
    session_service: DatabaseSessionService,
    session: Optional[Any] = None,
    profile_info: Dict = None,

) -> Dict[str, str]:
    """Initialize default job state with empty values.
    
    Args:
        app_name: Name of the application
        user_id: ID of the user
        session_id: ID of the session
        session_service: Database session service instance
        session: Optional session object
        
    Returns:
        Dict containing status and message of the operation
    
    Raises:
        Exception: If there's an error updating the session state
    """
    try:
        if not session:
            logger.warning(f"Session not found for user_id: {user_id}, session_id: {session_id}")
            return {"status": "error", "message": "Session not found"}

        logger.debug(f"Initializing default job state for session_id: {session_id}")
        print("profile:",profile_info)
        
        # Default state with empty placeholders
        state_delta = {
            "profile": profile_info,  # Profile information
            "candidate_info": "",
            # Custom matching job state
            "matching_id": "", # Matching id for matching job
            "custom_matching_id": "", # Custom matching id for custom matching job
            "matching_criteria": "", # Matching criteria for custom matching job
            "scoring_criteria": "", # Scoring criteria for custom matching job
            # TODO populate Origin url from the user's origin url
            "origin_url": "", # Origin url the website from where the user is initiating the custom matching job
            "is_image_upload": False, # Indicates if user uploaded an image with extracted content
        }

        # Create event with state delta
        event = Event(
            invocation_id=f"init_default_job_state_{session_id}",
            author="system",
            timestamp=time.time(),
            actions=EventActions(state_delta=state_delta)
        )

        await session_service.append_event(session, event)
        
        logger.debug(f"Successfully initialized default job state for session_id: {session_id}")
        return {"status": "success", "message": "Job state initialized successfully"}

    except Exception as e:
        error_msg = f"Failed to initialize default job state: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "message": error_msg}


async def initiate_iats_agent(query: str, user_id: str, session_id: str, chat: str, profile_info: dict = None, origin: str = None, parent_origin: str = None, company_id: str = None,extracted_info:str=None) -> Optional[str]:
    try:
        # Set default origins if not provided
        origin = origin
        if not origin:
            raise HTTPException(status_code=302, detail="Could not find origin.")

        parent_origin = parent_origin or BASE_URL
        logger.info("Starting iats agent initialization.")

        # Get profile and sub-agents
        profile_block, user_email, parent_origin = get_my_profile_block(profile_info, parent_origin)
        app_name="iats_sequential_flow"

        # Get child agents for iats_agent by company ID
        iats_sub_agents = AgentRegistryService.get_child_agent_names_for_company_by_id(company_id, "iats_agent")
        logger.info(f"Using database-driven child agents for iats_agent in company ID {company_id}: {iats_sub_agents}")
        
        if not iats_sub_agents:
            logger.warning(f"No child agents configured for iats_agent in company ID {company_id}")
            # Return professional authorization message instead of error
            unauthorized_message = "You are not authorized to access this agent. Please contact your administrator for access."
            formatted_response = IATSResponse(
                status="Unauthorized",
                response_type="text",
                full_response=unauthorized_message,
                event_id=None
            )
            return formatted_response.model_dump_json()

        initialized_agents = await safe_run_agents(
            iats_sub_agents,
            user_email, origin, session_id, company_id, app_name
        )

        # Initialize LLM model and agent dynamically
        model = get_llm_engine(agent_name='iats_agent', company_id=company_id)
        
        # Get dynamic instructions for IATS agent
        iats_agent_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="iats_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=profile_block,
            preloaded_context=None,
            mode="web",  # Default mode for IATS
            parent_origin=parent_origin
        )

        # Define callback with session_id bound
        async def load_itinerary(callback_context: CallbackContext):
            return await save_data_in_context(user_id, session_id, callback_context)
        new_chat = chat
        if extracted_info:
            logger.debug(f"adding extracted_information_from_image to llm_query_json")
            new_chat =f"this content was extracted from the uploaded image: {extracted_info} and this is the user's query: {chat}"
            
        iats_agent = LlmAgent(
            name="iats_agent",
            model=model,
            instruction=f"{IATS_GLOBAL_INSTRUCTIONS}\n{iats_agent_instructions}",
            description=agent_prompt_service.get_agent_description("iats_agent", company_id),
            tools=[memorize],
            sub_agents=initialized_agents,
            disallow_transfer_to_parent=True, 
            disallow_transfer_to_peers=True,
            output_key="iats_response",
            before_agent_callback=load_itinerary,
            after_agent_callback=after_agent_invocation_callback_context,
            after_model_callback=after_model_response_callback
        )

        output_formatter_agent = LlmAgent(
            name="output_formatter_agent",
            model=model,
            instruction=OUTPUT_FORMATTER_AGENT_PROMPT,
            description="formats the output according to instructions",
            output_schema=IATSResponse,
            disallow_transfer_to_parent=True, 
            disallow_transfer_to_peers=True,
            before_agent_callback=before_agent_invocation_callback_context,
            after_agent_callback=after_agent_invocation_callback_context,
            after_model_callback=after_model_response_callback_for_json_check
        )

        # Set up database session
        verified_db_url = create_db_url()
        if not verified_db_url:
            logger.error("Invalid database URL")
            raise HTTPException( status_code=500, detail=f"Database URL is not configured properly." )
        # Use in DatabaseSessionService
        sub_agents = [iats_agent]
        enable_output_formatter = os.getenv("ENABLE_OUTPUT_FORMATTER", "false").lower() == "true"

        if enable_output_formatter:
            sub_agents.append(output_formatter_agent)
            logger.info("Output formatter agent is enabled based on environment variable.")
        else:
            logger.info("Bypassing output formatter agent by default.")

        iats_sequential_flow = SequentialAgent(name="iats_sequential_flow", sub_agents=sub_agents)

        session_service = DatabaseSessionService(db_url=verified_db_url)
        session = await session_service.get_session(app_name="iats_sequential_flow", user_id=user_id, session_id=session_id)
        if session:
            logger.info(f"Session already exists for ID: {session_id}, reusing it.")
        else:
            session = await session_service.create_session(
                app_name="iats_sequential_flow",
                user_id=user_id,
                session_id=session_id
            )
            logger.info("Session created successfully.")

            await initialize_default_job_state("iats_sequential_flow", user_id, session_id, session_service, session, profile_info)

        # Set is_image_upload state based on extracted_info
        if extracted_info:
            logger.info("Setting is_image_upload state to True due to extracted_info presence")
            image_upload_event = Event(
                invocation_id=f"set_image_upload_state_{session_id}",
                author="system",
                timestamp=time.time(),
                actions=EventActions(state_delta={"is_image_upload": True})
            )
            await session_service.append_event(session, image_upload_event)
        else:
            logger.info("Setting is_image_upload state to False - no extracted_info")
            image_upload_event = Event(
                invocation_id=f"set_image_upload_state_{session_id}",
                author="system", 
                timestamp=time.time(),
                actions=EventActions(state_delta={"is_image_upload": False})
            )
            await session_service.append_event(session, image_upload_event)

        # Prepare query content
        llm_query_json = {"session_id": session_id, "my_personal_info": profile_info, "message": new_chat}
        content = types.Content(role='user', parts=[types.Part(text=json.dumps(llm_query_json, indent=2))])
        # Run agent and process response
        runner = Runner(agent=iats_sequential_flow, app_name="iats_sequential_flow", session_service=session_service)
        final_response, first_message_event_id, invocation_id = await get_final_agent_response(runner, user_id, session_id, content)
        

        if enable_output_formatter:
            return final_response
        else:
            # Manually format the response if the formatter is bypassed
            formatted_response = IATSResponse(
                status="Success",
                response_type="text",
                full_response=final_response,
                event_id=first_message_event_id
            )
            return formatted_response.model_dump_json()
    except LLMKeyNotSetException:
        # Re-raise LLMKeyNotSetException without modification to preserve its context
        raise
    except Exception as e:
        logger.error(f"Error running iats agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"IATS Agent failed to process the request: {str(e)}")
    finally:
        logger.info("iats agent execution completed.")

