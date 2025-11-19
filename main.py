import os
import uuid
import re
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException, Depends,Request,Header,status, WebSocket, Query,Response, UploadFile, File
from typing import Optional, List, Union
from fastapi.responses import JSONResponse
from app.helpers.user_agent import user_agent
from app.models.db_models import CustomMatchingCriteria, CustomMatchingResultsApplicantData
from app.services.current_user_info import get_current_profile
from app.services.llm_engine import get_llm_credentials_based_on_company_id
from app.core.exceptions import LLMKeyNotSetException, LLMConfigurationException
from app.services.redis_common_state import save_session_data,get_session_data,delete_session_data
from fastapi.middleware.cors import CORSMiddleware
from app.services.validate_llm_key import validate_completion, decrypt_hex_string
from app.utils.logger import logger
from app.services.email_notifier import send_exception_email
import json
from app.services.authenticate_agent import authenticate_invoke_kivo_agent, get_mode_from_request, get_origin_from_request
import uuid
from app.models.schema import CandidateSequentialMatchingRequest, DeleteSessionRequest, PMBoardAgentPayload, SequentialCompletionOutput, instruction_validation_response, instruction_validation_result, result_with_reasoning
from app.models.resume_parser_schema import ResumeParserPayload
from app.models.parser_schema import ResumeParserPayloadKivo
from app.helpers.resume_parser_agent import initiate_resume_parser_agent
from app.services.batchify_data import batchify
from pydantic import BaseModel, Field, ValidationError, model_validator
from app.helpers.transcribe_agent import invoke_transcribe_agent
from app.services.transcription import extract_query_from_voice_note
from app.services.batchify_data import process_story_individually, process_story_in_batches
from app.services.redis_common_state import save_session_data, delete_session_data
from dotenv import load_dotenv
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from app.models.schema import HRMSRequest, CoordinatorAgentRequest, InvokeAgentRequest
from app.helpers.triage import initiate_triage_agent
from app.services.vision_service import handle_vision_api
from app.helpers.crm_triage import initiate_crm_triage_agent
from openai import OpenAI
from pydantic import BaseModel
from app.utils.prompt import STORY_VALIDATION_INSTRUCTIONS
from fastapi.encoders import jsonable_encoder
from pm_board_data.core.config import BASE_URL, KIVO_API_BASE_URL
from app.helpers.iats import initiate_iats_agent
from typing import Dict, Optional, List, Union, Any, Literal
from app.socket.iats import iats_websocket_handler
from app.socket.workplace import workplace_websocket_handler
from app.socket.crm import crm_websocket_handler
from app.services.invoke_agent import invoke_agent
import time
import httpx
from sqlalchemy.orm import Session
from app.services.my_sql_client import get_db
from app.helpers.crm_faq_agent import invoke_crm_faq_agent
from app.helpers.crm_analysis_agent import invoke_crm_analysis_agent
from app.services.crm_current_user_info import get_crm_current_profile, get_crm_current_profile_for_faq
from app.services.edit_conversation import remove_conversation_included_from_event, remove_conversation_by_invocation_id, delete_iats_session
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.current_user_info import get_current_profile
from app.services.state_session_manager import get_user_session_details
from sqlalchemy.orm import aliased
import tempfile
import shutil
from pathlib import Path
from app.services.s3_service import s3_service
from app.services.image_validator import image_validator
# rexnord related imports
from rexnord.models.schema import RexnordTriageAgentRequest
from rexnord.helpers.rexnord_triage_agent import initiate_rexnord_agent
from app.utils.check_multiple_message import wait_for_single_query
import asyncio
from app.services.transcription import voice_note_formatted_query
from app.tools.fetch_image_on_intent import push_image_s3_url



# Network activity logging imports
from app.services.network_activity_dependency import log_network_activity_dependency, NetworkActivityContext, extract_network_details_from_request
from app.utils.whatsapp_button_formatter import process_whatsapp_response
from app.utils.whatsapp_button_formatter import remove_tags

# Load environment variables from .env file
load_dotenv()



class TranscriptionRequest(BaseModel):
    """
    Request model for audio transcription.
    
    This model defines the structure for transcription requests, including
    the audio file location and optional tracking identifiers.
    """
    s3_url: str = Field(..., description="URL to the audio file in S3")
    transaction_id: str = Field(default=None, description="Optional transaction identifier for tracking")
    message_id: int = Field(default=None, description="Optional message identifier")
    company_id: str = Field(..., description="Company identifier (required)")
    origin: str = Field(..., description="Origin of request (required)")

class CRMFAQRequest(BaseModel):
    """
    Request model for CRM FAQ queries.
    
    This model defines the structure for CRM-related questions,
    including the user's query, session context, and optional multimodal inputs.
    """
    query: str = Field(..., description="User's question about CRM processes or policies")
    session_id: str = Field(..., description="Session identifier for context and history")
    input_mode: Optional[str] = Field(None, description="Input mode: 'text', 'voice_note', or 'image'")
    input_data_url: Optional[Union[str, List[str]]] = Field(
        None,
        description="S3 URL or list of S3 URLs for voice note or image(s) when applicable"
    )

class RemoveConversationHistoryRequest(BaseModel):
    """
    Request model for removing conversation history.
    
    This model defines the structure for requests to remove chat history
    starting from a specific event, providing granular control over
    conversation data management.
    """
    session_id: str = Field(..., description="Session identifier for the conversation")
    event_id: str = Field(..., description="Event ID from which history will be removed (inclusive)")

class Attachment(BaseModel):
    """Attachment with type and URL"""
    attachment_type: str = Field(..., description="Type: 'image' or 'audio'")
    attachment_url: str = Field(..., description="URL to the attachment")

class CRMMessage(BaseModel):
    """CRM message with content and attachments"""
    message_type: str = Field(..., description="Type: 'incoming', 'outgoing', 'template'")
    content: str = Field(default="", description="Text content of the message")
    attachments: List[Attachment] = Field(default=[], description="List of attachments")

class ContactLabel(BaseModel):
    """Contact/Lead label with description"""
    name: str = Field(..., description="Label name")
    description: str = Field(..., description="Label description")

class CRMAnalysisRequest(BaseModel):
    """CRM email generation request with multimodal message support"""
    generation_type: str = Field(..., description="Email type: 'reminder', 'greet', 'follow_up', 'thank_you', 'general'")
    messages: List[CRMMessage] = Field(..., description="List of CRM messages with attachments")
    company_id: str = Field(..., description="Company ID for LLM config")
    full_name: str = Field(..., description="Recipient name (contact/lead)")
    current_user_name: str = Field(..., description="Sender name (CRM user)")
    user_query: Optional[str] = Field(None, description="Additional user instructions for email generation")
    label: Optional[List[ContactLabel]] = Field(default=[], description="Contact/lead labels with descriptions")
    session_id: Optional[str] = Field(None, description="Session identifier")

# Lifespan event handler for startup and shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    # Startup
    from app.services.periodic_event_cleanup import start_periodic_cleanup
    start_periodic_cleanup()
    logger.info("Application startup completed")
    yield
    # Shutdown (add cleanup code here if needed in the future)
    logger.info("Application shutdown")

# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# endpoint for home url
@app.get("/")
def server_connect(network_ctx: NetworkActivityContext = Depends(log_network_activity_dependency)):
    """
    Health check endpoint to verify server connectivity.
    
    Returns:
        dict: A simple status message confirming the server is running.
        
    Example:
        ```json
        {
            "status": "success",
            "message": "Echo from Kivo Agents Server"
        }
        ```
    """
    return {"status": "success", "message": "Echo from Kivo Agents Server"}


 
# Endpoint responsible to process story data with provided instructions and enforce required workflow.
@app.post("/invoke-pmboard-agent")
async def invoke_pm_board_agent(payload: PMBoardAgentPayload, request: Request,
    invoke_pm_board_agent_key: str = Depends(authenticate_invoke_kivo_agent), 
    network_ctx: NetworkActivityContext = Depends(log_network_activity_dependency),
    origin: str = Depends(get_origin_from_request)):
    """
    Process project management board stories with AI-powered analysis and workflow enforcement.
    
    This endpoint receives project stories and instructions, processes them using LLM agents,
    and returns analysis results. Stories are processed individually or in batches based on
    configuration settings.
    
    Args:
        payload (PMBoardAgentPayload): The request payload containing:
            - company_id: Company identifier to fetch LLM credentials
            - user_id: User identifier initiating the run
            - origin: Origin domain for credential scoping
            - project_id: Unique identifier for the project
            - data: Object containing project_instructions and stories array
        invoke_pm_board_agent_key (str): Authentication key for accessing this endpoint
        origin (str): Origin domain extracted from request headers
        
    Returns:
        dict: Processing results with status and execution details
        
    Raises:
        HTTPException: If LLM credentials are invalid or processing fails
        
    Example:
        ```json
        {
            "status": "success",
            "message": "PM_Board Agent executed",
            "processed_stories": 5,
            "execution_time": "2.5s"
        }
        ```
    """
    # Use provided identifiers (generate session; user_id provided by client)
    ka_session_id = f"pmb_session_{uuid.uuid4().hex}"
    ka_user_id = payload.user_id
    app_name = "pm_board_agent"
    company_id = payload.company_id
    
    logger.debug(f"Session created with session_id:{ka_session_id}, user_id:{ka_user_id}")
    
    try:
        payload_dict = payload.model_dump()
        project_id = payload_dict["project_id"]

        # Prefer payload origin when provided; fallback to header-derived origin
        incoming_origin = payload_dict.get("origin") or origin
        if incoming_origin is None:
            incoming_origin = KIVO_API_BASE_URL
            logger.warning(f"Origin not provided, using default: {incoming_origin}")
        else:
            incoming_origin = incoming_origin.lower()

        # Save session in Redis (like triage agent)
        if not incoming_origin.endswith("/"):
            incoming_origin = incoming_origin + "/"
        
        session_data_to_save = {
            "origin": incoming_origin,
            "company_id": company_id,
            "project_id": project_id,
            "user_id": ka_user_id
        }
        save_session_data(ka_session_id, session_data_to_save, app_name)
        logger.debug(f"Saved session data to Redis for session_id:{ka_session_id}")
        
        # Save session in Database (like triage agent)
        db = next(get_db())
        from app.services.state_session_manager import check_existing_session, create_user_session
        
        existing_session = check_existing_session(db, ka_session_id, app_name)
        if not existing_session:
            logger.info(f"Creating new DB session {ka_session_id} for user {ka_user_id}")
            create_user_session(db, ka_user_id, ka_session_id, app_name)
        else:
            logger.info(f"DB Session {ka_session_id} already exists")

        # Format project instructions as step-1, step-2, etc.
        project_instructions = [
            f"step-{index + 1}: {instruction}"
            for index, instruction in enumerate(payload_dict["data"]["project_instructions"])
        ]

        session_id = ka_session_id
        story_data = [
            {**story, "project_id": project_id, "user_id": ka_user_id}
            for story in payload_dict["data"]["stories"]
        ]
        # save to session
        story_batches = list(batchify(story_data, int(os.getenv("DATA_BATCH_SIZE"))))  # processing stories in batch (5)

        logger.debug(f"Formatted project instructions: {project_instructions}")
        logger.debug(f"Received data: {story_data}")

        # Choose processing method based on a condition (e.g., batch size or user preference)            
        # Process individually if the total number of stories is less than or equal to batch size
        process_results = await process_story_individually(
            story_data,
            ka_session_id,
            ka_user_id,
            company_id,
            app_name,
            incoming_origin,
            project_instructions,
            project_id,
        )
        
        # Process in batches (alternative to individual processing)
        # process_results = await process_story_in_batches(story_batches, ka_session_id, ka_user_id, company_id, app_name, incoming_origin, project_instructions)
        
        delete_session_data(ka_session_id, app_name) 
        logger.warning(f"Session data deleted for session_id:{ka_session_id}")
        logger.info(f"PM_Board Agent executed successfully with session_id:{ka_session_id}")
        return {
            "status": "success",
            "message": "PM_Board Agent executed",
            **process_results
        }

    except Exception as e:
        logger.error(f"Error invoking Kivo Agent: {e}", exc_info=True)
        # Extract network details for error email
        network_details = extract_network_details_from_request(request)
        send_exception_email(e, f"Error invoking Kivo Agent: {e}", network_details=network_details)
        return {"status": "error", "message": "Failed to execute agent"}

security = HTTPBearer()

async def get_base_url_from_request(request: Request) -> str:
    """
    Extract the base URL from the request, handling production vs development environments.
    
    This function determines the appropriate base URL based on the environment
    configuration and request headers. In production, it uses forwarded headers
    for proper URL reconstruction behind proxies.
    
    Args:
        request (Request): FastAPI request object containing headers and URL information
        
    Returns:
        str: The base URL for the current request
        
    Raises:
        HTTPException: If the host cannot be determined from request headers
        
    Example:
        >>> base_url = await get_base_url_from_request(request)
        >>> print(base_url)
        "https://api.example.com"
    """
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

@app.post("/transcribe-agent")
async def transcribe_agent(request: TranscriptionRequest, network_ctx: NetworkActivityContext = Depends(log_network_activity_dependency)):
    """
    Initiate audio transcription and processing from S3 URL using the Transcribe Agent.
    
    This endpoint starts asynchronous processing of audio files stored in S3. The audio
    is transcribed, summarized, classified as a lead, and the results are sent to CRM
    automatically in the background. This endpoint returns immediately with a confirmation
    that processing has been initiated.
    
    Args:
        request (TranscriptionRequest): The transcription request containing:
            - s3_url: URL to the audio file in S3
            - transaction_id: Optional transaction identifier for tracking
            - message_id: Optional message identifier
            - company_id: Company identifier (required)
            - origin: Origin of request (required)
            
    Returns:
        dict: Confirmation that audio processing has been initiated
        
    Example:
        ```json
        {
            "audio_status": true
        }
        ```
        
    Note:
        The actual transcription, summarization, and CRM integration happens
        asynchronously in the background. Results are not returned via this
        endpoint but are processed and stored automatically.
    """
    try:
        x = {}["missing_key"]
    except Exception as e:
        send_exception_email(
            error=e,
            context="Test error",
            session_id="test_123",
            file_path="main.py"  # ← This triggers AI analysis
        )


@app.post("/resume_parser_agent")
async def resume_parser_agent(
    payload: ResumeParserPayloadKivo,
    network_ctx: NetworkActivityContext = Depends(log_network_activity_dependency)
):
    """
    Parse and analyze resume content using AI-powered extraction.
    
    This endpoint processes resumes to extract relevant information such as skills,
    experience, education, and other professional details for job matching purposes.
    
    Args:
        payload (ResumeParserPayloadKivo): The resume parsing request containing:
            - resume_url: URL to the resume document
            - applied_job_title: Target job title for matching
            - applied_job_keywords: Keywords relevant to the job position
            
    Returns:
        dict: Parsed resume data with extracted information and analysis
        
    Raises:
        HTTPException: If resume parsing fails or encounters an error
        
    Example:
        ```json
        {
            "status": "success",
            "extracted_skills": ["Python", "JavaScript", "React"],
            "experience_years": 5,
            "education": "Bachelor's in Computer Science",
            "matching_score": 85.5
        }
        ```
    """
    logger.info(f"Received payload ====>>> : {payload}")
    try:
        result = await initiate_resume_parser_agent(
            resume_url=payload.resume_url,
            applied_job_title=payload.applied_job_title,
            applied_job_keywords=payload.applied_job_keywords,
            min_experience=payload.min_experience,
            max_experience=payload.max_experience,
            enable_real_time_updates=payload.enable_real_time_updates
        )
        if result.get("status") == "error":
            raise Exception(result.get("message", "Unknown error in resume parsing"))
            
        logger.info(f"Resume parsing completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Error in resume parser agent: {str(e)}", exc_info=True)
        # send_exception_email(e, f"Error in resume parser agent: {str(e)}")
        raise HTTPException(status_code=500, detail={"status": "error", "message": str(e)})
    
@app.post("/resume_parser_agent_psp")
async def resume_parser_agent(
    payload: ResumeParserPayload,
    resume_parser_agent_psp_key: str = Depends(authenticate_invoke_kivo_agent),
    network_ctx: NetworkActivityContext = Depends(log_network_activity_dependency)
):
    """
    Parse and analyze resume content with company-specific LLM credentials.
    
    This endpoint processes resumes using company-specific LLM models and credentials,
    providing enhanced parsing capabilities for enterprise users.
    
    Args:
        payload (ResumeParserPayload): The resume parsing request containing:
            - job_applicant_id: Unique identifier for the job applicant
            - resume_url: URL to the resume document
            - resume_text: Optional pre-extracted resume text to skip parsing
            - applied_job_title: Target job title for matching
            - applied_job_keywords: Keywords relevant to the job position
            - evaluation_criteria: List of evaluation criteria for assessment
            - job_profile_details: Job profile details including title, description, requirements
            - job_applicant_filled_qna: Additional Q&A data from job applicants
            - company_id: Company identifier for credential lookup
            - origin: Origin domain for authentication
            - resume_parsing: Boolean to control resume content parsing (default: True)
            - evaluation_result: Boolean to control evaluation report generation (default: False)
                * If resume_parsing=True and evaluation_result=False: Returns essential details immediately (partial), then parses resume in background and updates API (no evaluation)
                * If resume_parsing=True and evaluation_result=True: Returns essential details immediately (partial), then parses + evaluates in background and updates API
                * If resume_parsing=False and evaluation_result=True with resume_text provided: Runs evaluation synchronously, returns full evaluation immediately (NO API update, NO extracted_text in response)
                * If resume_parsing=False and evaluation_result=True without resume_text: Parses resume first then evaluates in background, updates API
                * If resume_parsing=False and evaluation_result=False: Skips all operations
        resume_parser_agent_psp_key (str): Authentication key for PSP access
        
    Returns:
        dict: Parsed resume data with extracted information and analysis
        
    Raises:
        HTTPException: If resume parsing fails or encounters an error
        
    Example:
        ```json
        {
            "status": "success",
            "extracted_skills": ["Python", "JavaScript", "React"],
            "experience_years": 5,
            "education": "Bachelor's in Computer Science",
            "matching_score": 85.5,
            "company_specific_insights": "..."
        }
        ```
    """
    try:
        # Log processing mode based on resume_parsing and evaluation_result flags
        if payload.resume_parsing and not payload.evaluation_result:
            logger.info(f"Processing mode: PARSE ONLY (resume_parsing=True, evaluation_result=False) - Will return essential details immediately, then parse resume in background and update API (no evaluation)")
        elif payload.resume_parsing and payload.evaluation_result:
            logger.info(f"Processing mode: PARSE + EVALUATION (resume_parsing=True, evaluation_result=True) - Will return essential details immediately, then parse resume in background with evaluation and update API")
        elif not payload.resume_parsing and payload.evaluation_result:
            if payload.resume_text:
                logger.info(f"Processing mode: EVALUATION ONLY with provided text (resume_parsing=False, evaluation_result=True, resume_text provided) - Will run evaluation synchronously and return full results immediately (NO API update)")
            else:
                logger.info(f"Processing mode: EVALUATION with auto-parsing (resume_parsing=False, evaluation_result=True, no resume_text) - Will parse resume first then evaluate")
        else:
            logger.info(f"Processing mode: SKIP ALL (resume_parsing=False, evaluation_result=False) - No operations will be performed")
        
        # Get LLM credentials based on company ID, app name, and origin
        try:
            model, llm_key, llm_base_url = get_llm_credentials_based_on_company_id(
                "resume_parser", 
                payload.company_id, 
                payload.origin
            )
            logger.info(f"Retrieved LLM credentials for app: resume_parser -->>, company: {payload.company_id}")
        except LLMKeyNotSetException as llm_error:
            logger.error(f"LLM credentials not configured for company {payload.company_id}: {str(llm_error)}")
            raise HTTPException(
                status_code=401, 
                detail={
                    "status": "error", 
                    "message": "Not authorized. Please contact the administrator.",
                    "error_type": "missing_llm_credentials"
                }
            )
        except LLMConfigurationException as config_error:
            logger.error(f"LLM configuration error for company {payload.company_id}: {str(config_error)}")
            raise HTTPException(
                status_code=401,
                detail={
                    "status": "error",
                    "message": "Not authorized. Please contact the administrator.",
                    "error_type": "invalid_llm_configuration"
                }
            )

        # Log experience range if available in job_profile_details
        if payload.job_profile_details:
            min_exp = payload.job_profile_details.get_min_experience()
            max_exp = payload.job_profile_details.get_max_experience()
            if min_exp is not None and max_exp is not None:
                logger.info(f"Experience range from job_profile_details: {min_exp}-{max_exp} years")

        result = await initiate_resume_parser_agent(
            job_applicant_id=str(payload.job_applicant_id) if payload.job_applicant_id is not None else None,
            resume_url=payload.resume_url,
            resume_text=payload.resume_text,
            applied_job_title=payload.applied_job_title,
            applied_job_keywords=payload.applied_job_keywords,
            evaluation_criteria=payload.evaluation_criteria,
            job_profile_details=payload.job_profile_details.model_dump() if payload.job_profile_details else None,
            job_applicant_filled_qna=payload.job_applicant_filled_qna,
            min_experience=payload.min_experience,
            max_experience=payload.max_experience,
            llm_key=llm_key,
            llm_base_url=llm_base_url,
            model=model,
            company_id=str(payload.company_id),
            origin=payload.origin,
            resume_parser_access_token=payload.resume_parser_access_token,
            rails_api_url=payload.rails_api_url,
            enable_real_time_updates=payload.enable_real_time_updates,
            resume_parsing=payload.resume_parsing,
            evaluation_result=payload.evaluation_result
        )
        
        # Handle None result
        if result is None:
            raise Exception("Resume parser agent returned None - internal processing error")
            
        if result.get("status") == "error":
            raise Exception(result.get("message", "Unknown error in resume parsing"))
            
        logger.info(f"Resume parsing completed successfully")
        return result
        
    except HTTPException:
        # Re-raise HTTPException without modification to preserve status codes
        raise
    except Exception as e:
        logger.error(f"Error in resume parser agent: {str(e)}", exc_info=True)
        # send_exception_email(e, f"Error in resume parser agent: {str(e)}")
        raise HTTPException(status_code=500, detail={"status": "error", "message": str(e)})

# Endpoint to invoke triage agent whch is responsible to route queries to respective sub-agents like hrms_agent, pm_board_story_agent, ats_agent, calling_agent.
@app.post("/invoke-coordinator-agent")
async def invoke_triage_agent(
    request_data: CoordinatorAgentRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    origin: str = Depends(get_origin_from_request),
    mode: str = Depends(get_mode_from_request),
    network_ctx: NetworkActivityContext = Depends(log_network_activity_dependency)
):
    """
    Invoke the Coordinator Agent to route queries to appropriate sub-agents.
    
    This endpoint serves as the main entry point for user queries, automatically
    routing them to the most appropriate specialized agent (HRMS, PM Board, ATS,
    Calling, etc.) based on the query content and context.
    
    Args:
        request_data (CoordinatorAgentRequest): The coordination request containing:
            - query: User's question or request
            - query_id: Unique identifier for the query
            - parent_origin: Origin domain of the parent application
        credentials (HTTPAuthorizationCredentials): Bearer token for authentication
        origin (str): Origin domain extracted from request headers
        mode (str): Operation mode (e.g., 'production', 'development')
        
    Returns:
        dict: Coordination results with agent response and session details
        
    Raises:
        HTTPException: If authentication fails or coordination encounters an error
        
    Example:
        ```json
        {
            "status": "success",
            "type": "final_response",
            "message": "Coordinator Agent invoked",
            "query": "What are my leave balances?",
            "response": "Your leave balances are...",
            "session_id": "session_123",
            "event_id": "event_456"
        }
        ```
    """
    # Initialize variables that might be needed in exception handling
    profile_info = None
    company_id = None
    
    try:
        logger.info(f"[origin] from headers is: {origin}")
        logger.info(f"[mode] from headers is: {mode}")

        # Extract token from Authorization header
        token = credentials.credentials
        # Extract data from request body
        query = request_data.query
        user_id = request_data.query_id
        session_id = f"session_{user_id}"
        parent_origin = request_data.parent_origin
        preloaded_context = request_data.preloaded_context
        logger.info(f"preloaded_context is {preloaded_context}")
        logger.info(f"parent_origin: {parent_origin}")
        app_name = "triage_agent"
        
        # Update network activity context with session info
        network_ctx.set_session_id(session_id)
        # Optional multimodal inputs
        input_mode = request_data.input_mode
        input_data_url = request_data.input_data_url

        # logger.info(f"Received origin: {origin}, \n query_id: {query_id}, \n token: {token}")

        if origin is None:
            origin = KIVO_API_BASE_URL
            logger.warning(f"Origin not provided, using default: {origin}")
        else:  
            origin = origin.lower()
        if not token or not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required token or number"
            )

        profile_info = await get_current_profile(token, origin) 
        company_id = profile_info.get('company_id')
        if not company_id:
            logger.error(f"Company ID not found in profile, cannot load llm keys.")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"status": "error", "message": "Cannot load llm keys. Contact administrator."}
            )
        
        # Update network activity context with user info
        network_ctx.set_user_id(profile_info.get('email', user_id))
        network_ctx.set_company_id(str(company_id))
        if not profile_info:
            logger.error(f"Profile information not found for query_id: {user_id}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "status": "error",
                    "message": "You do not have access. Please contact the administrator."
                }
            )

        # Determine the active app namespace for image/session data based on role
        is_admin_or_hr = bool(profile_info.get('is_admin') or profile_info.get('is_hr'))
        app_name_for_session = "triage_agent" if is_admin_or_hr else "user_agent"

        # If voice note mode, transcribe now that we have company_id and origin
        if input_mode == 'voice_note' and input_data_url:
            logger.debug(f"[Triage] input_mode=voice_note, starting transcription")
            query_extracted_from_voice = await extract_query_from_voice_note(
                s3_url=input_data_url,
                company_id=company_id,
                origin=origin,
                app_name=f"{app_name}_transcribe"
            )
            query = voice_note_formatted_query(query_extracted_from_voice)
            
            logger.info(f"[Triage] Query received from voice note - {query}")

        # If image mode, run vision analysis to extract info from image(s)
        extracted_info_from_image = None
        extracted_info_for_queue = None  # carry image extracted text into the queued item
        if input_mode == 'image' and input_data_url:
            try:
                # Normalize to list for consistent handling
                urls = input_data_url if isinstance(input_data_url, list) else [input_data_url]
                logger.debug(f"[Triage] input_mode=image, starting vision analysis for {len(urls)} URL(s)")

                extracted_chunks = []
                for idx, url in enumerate(urls):
                    try:
                        # Persist each image URL in session context for downstream tools (keep last few)
                        try:
                            push_image_s3_url(session_id, app_name_for_session, url)
                            
                        except Exception:
                            pass

                        vision_request_data = {
                            "query": query,
                            "session_id": session_id,
                            "user_id": user_id,
                            "origin": origin,
                            "app_name": app_name_for_session,
                            "image_url": url
                        }
                        logger.debug(f"[Triage] Vision analysis starting for image {idx+1}: {url}")
                        chunk = await handle_vision_api(vision_request_data, origin, company_id)
                        if chunk:
                            extracted_chunks.append(f"Image {idx+1}: {chunk}")
                    except Exception as inner_e:
                        logger.error(f"[Triage] Vision analysis failed for one image: {inner_e}")

                if extracted_chunks:
                    # Combine all extracted info into a single string for the agent
                    extracted_info_from_image = "\n\n".join(extracted_chunks)
                    extracted_info_for_queue = extracted_info_from_image
                    logger.debug("Captured combined extracted_info_for_queue for image items")
                logger.info("[Triage] Vision analysis completed for image upload(s)")
            except Exception as ve:
                logger.error(f"[Triage] Vision analysis failed: {ve}", exc_info=True)
            
        company_id=profile_info.get("company_id", "")
        if not company_id:
            logger.error(f"Company ID not found for query_id: {user_id}")
            return {
                "status": "error",
                "message": "Company ID not found"
            }
        query_uuid=str(uuid.uuid4())
        # Get session data from Redis
        session_data = get_session_data(session_id)
        if not session_data:
            # Creating new session with token and empty history
            obj=[{
                "query": query,
                "index": query_uuid,
                # attach image extracted info for merging (None for non-image)
                "extracted_info": extracted_info_for_queue if input_mode == 'image' else None
            }]
            save_session_data(session_id, {"token": token, "origin": origin,"check_queries":json.dumps(obj),"company_id":company_id})
            
        else:
            # Load history from session data
            print("saving token in session data.")
            session_data["token"] = token
            session_data["origin"] = origin
            queries=json.loads(session_data.get("check_queries", "[]"))
            queries.append({
                "query": query,
                "index": query_uuid,
                # attach image extracted info for merging (None for non-image)
                "extracted_info": extracted_info_for_queue if input_mode == 'image' else None
            })
            query=queries[0].get("query", "") if len(queries) > 0 else query
            session_data["check_queries"]=json.dumps(queries)
            session_data["company_id"]=company_id
            save_session_data(session_id, session_data)
        
        # Check for multiple queries and wait if necessary
        logger.info(f"Checking for multiple queries before executing triage agent for session: {session_id}")
        can_proceed = await wait_for_single_query(session_id,query_uuid)
        
        if not can_proceed:
            logger.warning(f"Timeout waiting for single query - proceeding with execution anyway")
        session_data = get_session_data(session_id)
        queries = json.loads(session_data["check_queries"])
        if len(queries) <= 0:
            logger.info(f"No queries found in session (expected after merge): {session_id}")
            return Response(status_code=204)
        query=queries[0].get("query", "") if len(queries) > 0 else query
        logger.debug(f"query: {query}")
        # Initiate triage agent 
        logger.info(f"Admin/Hr Role of received profile is: {profile_info.get('is_admin')}")
        if profile_info.get('is_admin') or profile_info.get('is_hr'):

            triage_result = await initiate_triage_agent(
                query,
                user_id=user_id,
                session_id=session_id,
                profile_info=profile_info,
                origin=origin,
                parent_origin=parent_origin,
                mode=mode,
                token=token,
                app_name=app_name,
                extracted_info=extracted_info_from_image,
                preloaded_context=preloaded_context,
                input_data_url=input_data_url
            )
                    
            # Safely unpack the result
            if isinstance(triage_result, tuple) and len(triage_result) == 3:
                response, event_id, invocation_id = triage_result
            else:
                logger.error(f"Unexpected return format from triage agent: {triage_result}")
                raise HTTPException(status_code=500, detail="Coordinator Agent returned unexpected response format")

            # Process the request (this is a placeholder for actual processing logic)

        else:
            app_name = "user_agent"
            logger.info(f"Invoking user agent with app_name: {app_name}")
            # If image info is available and using user_agent, embed it into query
            query_for_user_agent = query
            if extracted_info_from_image:
                try:
                    if isinstance(input_data_url, list):
                        for url in input_data_url:
                            push_image_s3_url(session_id, app_name_for_session, url)
                    elif input_data_url:
                        push_image_s3_url(session_id, app_name_for_session, input_data_url)
                except Exception:
                    pass
                query_for_user_agent = (
                    f"This content was extracted from the uploaded image: {extracted_info_from_image} "
                    f"and this is the user's query: {query}"
                )
            user_result = await user_agent(
                query_for_user_agent,
                user_id=user_id,
                session_id=session_id,
                profile_info=profile_info,
                origin=origin,
                parent_origin=parent_origin,
                mode=mode,
                token=token,
                app_name=app_name,
                extracted_info=extracted_info_from_image,
                preloaded_context=preloaded_context
            )

            if isinstance(user_result, tuple) and len(user_result) == 3:
                response, event_id, invocation_id = user_result
            else:
                logger.error(f"Unexpected return format from user agent: {user_result}")
                raise HTTPException(status_code=500, detail="User Agent returned unexpected response format")
        session_data = get_session_data(session_id)
        queries = json.loads(session_data["check_queries"])
        if len(queries) > 1:
            # Merge ALL queries into a single consolidated query
            all_query_texts = []
            for i, q in enumerate(queries):
                base_text = (q.get('query') or '').strip()
                image_info = q.get('extracted_info')
                if image_info:
                    merged_part = f"This content was extracted from the uploaded image: {image_info} and this is the user's query: {base_text}"
                else:
                    merged_part = base_text
                if merged_part:
                    all_query_texts.append(merged_part)
            
            # Create merged query - join with space, or structure as numbered list if many queries
            if len(all_query_texts) <= 3:
                new_merged_query = " ".join(all_query_texts)
            else:
                # For many queries, structure as numbered list for clarity
                numbered_queries = [f"{i+1}. {q}" for i, q in enumerate(all_query_texts)]
                new_merged_query = "I have multiple questions: " + " ".join(numbered_queries)
            
            logger.info(f"Merging {len(queries)} queries into: '{new_merged_query[:100]}...'")
            
            # Keep the structure similar - update the last query in the list with merged content
            queries[-1]["query"] = new_merged_query
            # Clear extracted_info to avoid double-wrapping in future merges
            if 'extracted_info' in queries[-1]:
                queries[-1].pop('extracted_info', None)
            logger.debug(f"Merged {len(queries)-1} queries into final query")
            logger.debug(f"deleting session of the user using invocation_id: {invocation_id}")
            if invocation_id:
                delete_events = await remove_conversation_by_invocation_id(session_id, user_id, invocation_id, app_name)
                if delete_events["status"] == "success":
                    logger.debug(f"events successfully deleted using invocation_id")
                else:
                    logger.error(f"failed to delete events using invocation_id: {delete_events}")
            else:
                # Fallback to event_id based deletion if invocation_id is not available
                logger.warning("No invocation_id available, falling back to event_id based deletion")
                delete_events = await remove_conversation_included_from_event(session_id, user_id, event_id, app_name)
                if delete_events["status"] == "success":
                    logger.debug(f"events successfully deleted using event_id fallback")
                else:
                    logger.error(f"failed to delete events using event_id fallback: {delete_events}")
            
            # Remove all queries except the last one (which now contains the merged query)
            queries = [queries[-1]]
            
            logger.info(f"After merging: {len(queries)} query remaining with consolidated content")
            
            # Save the updated queries back to Redis
            session_data["check_queries"] = json.dumps(queries)
            save_session_data(session_id, session_data)
            
            return Response(status_code=204)
        elif len(queries) == 1:
            # Single query - clear the queue and return success
            new_query = queries[0].get("query", "")
            session_data["check_queries"] = json.dumps([])
            save_session_data(session_id, session_data)

            # Determine if channel is WhatsApp
            is_whatsapp = str(mode or "").lower() == "whatsapp"
            logger.info(f"is_whatsapp: {is_whatsapp}")
            logger.info(f"response: {response}")
            # Process WhatsApp interactive buttons only for WhatsApp mode (use original response)
            interactive = None
            if is_whatsapp:
                logger.info(f"processing whatsapp response")
                interactive = (
                    process_whatsapp_response(
                        response=f"{response}",
                        query=new_query,
                        mode=mode,
                        origin=origin,
                        company_id=company_id,
                        app_name=app_name
                    )
                )
            # tag cleanup logic
            response = remove_tags(response)

            response_payload = {
                "status": "success",
                "type": "final_response",
                "message": f"Coordinator Agent invoked",
                "query": new_query,
                "response": response,
                "session_id": session_id,
                "event_id": event_id,
            }

            if interactive:
                response_payload["whatsapp_interactive"] = interactive

            return response_payload
        else:
            logger.info(f"No --- queries found in session (expected after processing): {session_id}")
            return Response(status_code=204)

    except Exception as e:
        
        logger.error(f"Error invoking Coordinator Agent: {e}", exc_info=True)
        # Attempt to remove the current (failed) query from Redis so that it does not block the queue
        try:
            session_data = get_session_data(session_id)
            if session_data and "check_queries" in session_data:
                queries = json.loads(session_data["check_queries"])
                # If the first query corresponds to the current request (by uuid), remove it
                failed_query_uuid = query_uuid if "query_uuid" in locals() else None
                # Remove the first element if it matches or simply pop index 0 to unblock queue
                query_removed = False
                if failed_query_uuid and queries:
                    if queries[0].get("index") == failed_query_uuid:
                        queries.pop(0)
                        query_removed = True
                    else:
                        # UUID doesn't match, but still pop to avoid blocking
                        queries.pop(0)
                        query_removed = True
                elif queries:
                    # Fallback: always pop index 0 to avoid blocking when no UUID
                    queries.pop(0)
                    query_removed = True
                
                if query_removed:
                    session_data["check_queries"] = json.dumps(queries)
                    save_session_data(session_id, session_data)
                    logger.info(f"Removed failed query from session {session_id} queue after error.")
        except Exception as cleanup_error:
            logger.error(f"Failed to clean up queue after error: {cleanup_error}", exc_info=True)
        
        # Extract network details for error email
        network_details = extract_network_details_from_request(request)
        send_exception_email(
            e, 
            f"Error invoking Coordinator Agent: {str(e)} | Session ID: {session_id} | Query: {query} | Origin: {origin} | Company ID: {company_id}", 
            session_id=session_id, 
            origin=origin, 
            company_id=company_id,
            network_details=network_details
        )
        raise HTTPException(status_code=500, detail="Failed to invoke Coordinator Agent")

# @app.post("/invoke-coordinator-agent")
# async def invoke_coordinator_agent(
#     request_data: CoordinatorAgentRequest,
#     credentials: HTTPAuthorizationCredentials = Depends(security)
# ):
#     """
#     Endpoint to invoke the Coordinator Agent.
#     """
#     return await invoke_agent(
#         request_data=request_data,
#         credentials=credentials,
#         agent_name="Coordinator",
#         initiate_agent_func=initiate_triage_agent  # Assuming initiate_triage_agent is defined
#     )

@app.post("/invoke-iats-agent")
async def invoke_iats_agent_endpoint(
    request_data: InvokeAgentRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    origin: str = Depends(get_origin_from_request),
    network_ctx: NetworkActivityContext = Depends(log_network_activity_dependency)
):
    """
    Invoke the IATS (Intelligent Applicant Tracking System) Agent.
    
    This endpoint processes requests for the IATS agent, which handles applicant
    tracking, job matching, and recruitment-related tasks using AI capabilities.
    
    Args:
        request_data (InvokeAgentRequest): The IATS agent request containing:
            - query: User's question or request
            - query_id: Unique identifier for the query
            - origin: Origin domain for authentication
        credentials (HTTPAuthorizationCredentials): Bearer token for authentication
        origin (str): Origin domain extracted from request headers
        
    Returns:
        dict: IATS agent response and processing results
        
    Raises:
        HTTPException: If authentication fails or IATS processing encounters an error
        
    Example:
        ```json
        {
            "status": "success",
            "agent": "IATS",
            "response": "I found 5 matching candidates...",
            "query_id": "query_123"
        }
        ```
    """
    logger.info("Invoked IATS endpoint")
    request_data.origin = origin
    return await invoke_agent(
        request_data=request_data,
        credentials=credentials,
        agent_name="IATS",
        initiate_agent_func=initiate_iats_agent  # Assuming initiate_iats_agent is defined
    )

# Endpoint responsible to validate story instruction for pm-board checks duplicacy, enhance them with llms, check for best recipient, etc. 
@app.post("/pmboard-agent/validate-instruction")
def validate_pm_board_instruction(payload:instruction_validation_response, validate_instruction: str = Depends(authenticate_invoke_kivo_agent), network_ctx: NetworkActivityContext = Depends(log_network_activity_dependency)):
    """
    Validate and enhance project management board instructions using AI analysis.
    
    This endpoint analyzes project instructions for:
    - Duplicate detection against existing instructions
    - Enhancement suggestions using LLM capabilities
    - Appropriate recipient recommendations based on team structure
    
    Args:
        payload (instruction_validation_response): The validation request containing:
            - instructions_list: Existing project instructions for comparison
            - user_instruction: New instruction to validate and enhance
            - team_members: Available team members for recipient suggestions
        validate_instruction (str): Authentication key for instruction validation
        
    Returns:
        JSONResponse: Enhanced instruction with validation results and recommendations
        
    Raises:
        HTTPException: If validation fails or encounters an error
        
    Example:
        ```json
        {
            "enhanced_instruction": "Updated instruction text...",
            "is_duplicate": false,
            "duplicate_confidence": 0.1,
            "suggested_recipients": ["user1@company.com", "user2@company.com"],
            "enhancement_reasoning": "Instruction was enhanced to include..."
        }
        ```
    """
    try:
        logger.info(f"Received payload for pm-board/validate-instruction: {payload}")

        if payload.company_id is None or payload.origin is None:
            raise HTTPException(status_code=400, detail="Company ID and origin are required")
        
        model, llm_key, llm_base_url = get_llm_credentials_based_on_company_id("pm_board_agent", payload.company_id, payload.origin)

        client = OpenAI(
            api_key=llm_key, 
            base_url=llm_base_url  
        )
        input=[
                { "role": "system", "content": STORY_VALIDATION_INSTRUCTIONS },
                {
                    "role": "user",
                    "content": f"""
                                Enhance user_instruction if relevant, check its duplicacy with `instructions_list`, and suggest appropiate recipients (can be multiple).
                                instructions_list:
                                {payload.instructions_list}

                                user_instruction:
                                {payload.user_instruction}

                                team_members:
                                {payload.team_members}
                                """
                }
            ]
        logger.info(f"Processing instruction with llm")

        response = client.responses.parse(
            model=model,
            input=input,
            text_format=result_with_reasoning,
        )

        logger.debug(f"Received response from LLM: {response.output_parsed}")
        # converted object to json string
        json_parsed_response = json.dumps(jsonable_encoder(response.output_parsed), indent=2)

        return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=json_parsed_response
            )
    
    except ValidationError as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/custom-matching/results/{custom_matching_id}")
async def get_matching_results(
    custom_matching_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=500000),
    origin: Optional[str] = Query(None),
    job_matching_percentage_filter: Optional[Literal["<50", ">=50", ">50", ">60", ">70", ">80", ">90"]] = Query(None),
    credentials: HTTPAuthorizationCredentials = Depends(security), 
    db: Session = Depends(get_db),
    network_ctx: NetworkActivityContext = Depends(log_network_activity_dependency)
):
    """
    Retrieve paginated custom matching results for job applicants.
    
    This endpoint fetches job applicant matching results based on custom matching criteria,
    with support for pagination and filtering by job matching percentage. Results are
    filtered by company to ensure data isolation.
    
    Args:
        custom_matching_id (str): Unique identifier for the custom matching job
        page (int): Page number for pagination (minimum: 1)
        limit (int): Number of results per page (minimum: 1, maximum: 500000)
        origin (Optional[str]): Origin domain for authentication (defaults to demo if "demo")
        job_matching_percentage_filter (Optional[str]): Filter by matching percentage:
            - "<50": Less than 50%
            - ">=50": 50% or higher
            - ">50": Greater than 50%
            - ">60": Greater than 60%
            - ">70": Greater than 70%
            - ">80": Greater than 80%
            - ">90": Greater than 90%
        credentials (HTTPAuthorizationCredentials): Bearer token for authentication
        db (Session): Database session for data access
        
    Returns:
        dict: Paginated matching results with metadata
        
    Raises:
        HTTPException: If no results found (204) or authentication fails (403)
        
    Example:
        ```json
        {
            "custom_matching_id": "match_123",
            "page": 1,
            "limit": 10,
            "count": 10,
            "total": 45,
            "job_applicants": [
                {
                    "job_applicant_id": 101,
                    "job_matching_percentage": 85.5,
                    "job_matching_percentage_reason": "Strong Python skills, relevant experience..."
                }
            ]
        }
        ```
    """
    token = credentials.credentials
    logger.info(f"Token received: {token} and origin {origin}")

    if origin == "demo":
        origin = "https://demo.kivo.ai"

    profile_info = await get_current_profile(token, origin)
    logger.debug(f"profile_info: {profile_info}")

    company_id = profile_info["company_id"]
    logger.info(f"Looking for matching_id={custom_matching_id} for company_id={company_id}")
    
    # Update network activity context
    network_ctx.set_user_id(profile_info.get('email', ''))
    network_ctx.set_company_id(str(company_id))
    offset = (page - 1) * limit

    # Perform a JOIN to enforce company_id check via criteria table
    Criteria = aliased(CustomMatchingCriteria)
    Results = aliased(CustomMatchingResultsApplicantData)

    base_query = db.query(Results).join(
        Criteria,
        Results.custom_matching_id == Criteria.custom_matching_id
    ).filter(
        Results.custom_matching_id == custom_matching_id,
        Criteria.company_id == company_id
    )

    # Add job_matching_percentage filter if provided
    if job_matching_percentage_filter:
        if job_matching_percentage_filter == "<50":
            base_query = base_query.filter(Results.matching_score < 50)
        elif job_matching_percentage_filter == ">=50":
            base_query = base_query.filter(Results.matching_score >= 50)
        elif job_matching_percentage_filter == ">50":
            base_query = base_query.filter(Results.matching_score > 50)
        elif job_matching_percentage_filter == ">60":
            base_query = base_query.filter(Results.matching_score > 60)
        elif job_matching_percentage_filter == ">70":
            base_query = base_query.filter(Results.matching_score > 70)
        elif job_matching_percentage_filter == ">80":
            base_query = base_query.filter(Results.matching_score > 80)
        elif job_matching_percentage_filter == ">90":
            base_query = base_query.filter(Results.matching_score > 90)
        
        logger.info(f"Filtering by job_matching_percentage: {job_matching_percentage_filter}")

    total_count = base_query.count()

    results = base_query.order_by(
        Results.matching_score.desc()
    ).offset(offset).limit(limit).all()

    if not results:
        logger.warning(f"No matching results found for ID: {custom_matching_id} and company_id: {company_id}")
        raise HTTPException(status_code=204, detail="No content found")
    response = [
        {
            "job_applicant_id": row.applicant_id,
            "job_matching_percentage": float(row.matching_score) if row.matching_score else None,
            "job_matching_percentage_reason": row.matching_score_reasoning
        }
        for row in results
    ]

    return {
        "custom_matching_id": custom_matching_id,
        "page": page,
        "limit": limit,
        "count": len(response),
        "total": total_count,
        "job_applicants": response
    }


@app.websocket("/ws/invoke-iats-agent")
async def websocket_invoke_iats_agent(websocket: WebSocket):
    """
    WebSocket endpoint for real-time IATS agent communication.
    
    This endpoint establishes a WebSocket connection for real-time interaction
    with the IATS agent, enabling streaming responses and live updates.
    
    Args:
        websocket (WebSocket): The WebSocket connection object
        
    Note:
        This endpoint handles the WebSocket connection lifecycle and delegates
        to the iats_websocket_handler for actual message processing.
    """
    await iats_websocket_handler(websocket)

@app.websocket("/ws/invoke-workplace-agent")
async def websocket_invoke_workplace_agent(websocket: WebSocket):
    """
    WebSocket endpoint for real-time Workplace (Triage) agent communication.
    
    This endpoint establishes a WebSocket connection for real-time interaction
    with the Workplace agent, enabling streaming responses and live updates.
    The Workplace agent routes queries to appropriate sub-agents like HRMS,
    PM Board, ATS, Calling, etc. based on the query content and context.
    
    Args:
        websocket (WebSocket): The WebSocket connection object
        
    Note:
        This endpoint handles the WebSocket connection lifecycle and delegates
        to the workplace_websocket_handler for actual message processing.
    """
    await workplace_websocket_handler(websocket)

@app.websocket("/ws/invoke-crm-triage-agent")
async def websocket_invoke_crm_triage_agent(websocket: WebSocket):
    """
    WebSocket endpoint for real-time CRM Triage agent communication.
    
    This endpoint establishes a WebSocket connection for real-time interaction
    with the CRM Triage agent, enabling streaming responses and live updates.
    The CRM Triage agent handles customer relationship management queries and
    routes them to appropriate CRM sub-agents when they become available.
    
    Args:
        websocket (WebSocket): The WebSocket connection object
        
    Note:
        This endpoint handles the WebSocket connection lifecycle and delegates
        to the crm_websocket_handler for actual message processing.
    """
    await crm_websocket_handler(websocket)

@app.post("/invoke_crm_faq_agent")
async def invoke_crm_agent(payload: CRMFAQRequest, request: Request, network_ctx: NetworkActivityContext = Depends(log_network_activity_dependency)):
    """
    Invoke the CRM FAQ agent to answer customer relationship management questions.
    
    This endpoint processes CRM-related queries using AI-powered FAQ capabilities,
    providing accurate and contextual answers based on the user's session and profile.
    Supports text, voice notes, and image inputs for multimodal interactions.
    Handles multiple concurrent queries by queuing and consolidating them.
    
    Args:
        payload (CRMFAQRequest): The CRM FAQ request containing:
            - query: User's question about CRM processes or policies
            - session_id: Session identifier for context and history
            - input_mode: Optional input mode ('text', 'voice_note', 'image')
            - input_data_url: Optional S3 URL for voice note or image
            
    Returns:
        dict: CRM FAQ response with answer and metadata
        
    Raises:
        HTTPException: If CRM FAQ processing fails or encounters an error
        
    Example:
        ```json
        {
            "status": "success",
            "query": "How do I update customer information?",
            "answer": "To update customer information, navigate to...",
            "session_id": "session_123"
        }
        ```
    """
    # Initialize variables that might be needed in exception handling
    query_uuid = None
    session_id = payload.session_id
    
    try:
        profile_info = await get_crm_current_profile_for_faq(payload.session_id)
        
        if not profile_info:
            logger.error(f"Profile information not found for session_id: {payload.session_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"status": "error", "message": "Profile information not found. Please contact the administrator."}
            ) 
        company_id = os.getenv("CRM_ACCOUNT_ID", "3")
        
        # Update network activity context
        network_ctx.set_session_id(payload.session_id)
        network_ctx.set_company_id(str(company_id))
        if profile_info.get('email'):
            network_ctx.set_user_id(profile_info['email'])
        
        # Initialize variables for multimodal processing
        query = payload.query
        extracted_info_from_image = None
        origin = KIVO_API_BASE_URL  # Use default origin for CRM FAQ
        app_name = "crm_faq_agent"
        
        # If voice note mode, transcribe the audio
        if payload.input_mode == 'voice_note' and payload.input_data_url:
            logger.debug(f"[CRM FAQ] input_mode=voice_note, starting transcription")
            try:
                query_extracted_from_voice = await extract_query_from_voice_note(
                    s3_url=payload.input_data_url,
                    company_id=company_id,
                    origin=origin,
                    app_name=f"{app_name}_transcribe"
                )
                query = voice_note_formatted_query(query_extracted_from_voice)
                logger.info(f"[CRM FAQ] Query received from voice note - {query}")
            except Exception as ve:
                logger.error(f"[CRM FAQ] Voice transcription failed: {ve}", exc_info=True)
                raise HTTPException(status_code=400, detail="Failed to transcribe voice note")
        
        # If image mode, run vision analysis to extract info from image
        extracted_info_for_queue = None  # carry image extracted text into the queued item
        if payload.input_mode == 'image' and payload.input_data_url:
            try:
                # Normalize to list for consistent handling
                urls = payload.input_data_url if isinstance(payload.input_data_url, list) else [payload.input_data_url]
                logger.debug(f"[CRM FAQ] input_mode=image, starting vision analysis for {len(urls)} URL(s)")

                extracted_chunks = []
                for idx, url in enumerate(urls):
                    try:
                        vision_request_data = {
                            "query": query,
                            "session_id": payload.session_id,
                            "user_id": payload.session_id,  # Using session_id as user_id for CRM FAQ
                            "origin": origin,
                            "app_name": app_name,
                            "image_url": url
                        }
                        logger.debug(f"[CRM FAQ] Vision analysis starting for image {idx+1}: {url}")
                        chunk = await handle_vision_api(vision_request_data, origin, company_id)
                        if chunk:
                            extracted_chunks.append(f"Image {idx+1}: {chunk}")
                    except Exception as inner_e:
                        logger.error(f"[CRM FAQ] Vision analysis failed for one image: {inner_e}")

                if extracted_chunks:
                    extracted_info_from_image = "\n\n".join(extracted_chunks)
                    extracted_info_for_queue = extracted_info_from_image
                    logger.debug("Captured combined extracted_info_for_queue for CRM FAQ image items")
                logger.info("[CRM FAQ] Vision analysis completed for image upload(s)")
            except Exception as ve:
                logger.error(f"[CRM FAQ] Vision analysis failed: {ve}", exc_info=True)
                raise HTTPException(status_code=400, detail="Failed to analyze image")
        
        query_uuid = str(uuid.uuid4())
        # Get session data from Redis
        session_data = get_session_data(session_id)
        if not session_data:
            # Creating new session with empty history
            obj = [{
                "query": query,
                "index": query_uuid,
                # attach image extracted info for merging (None for non-image)
                "extracted_info": extracted_info_for_queue if payload.input_mode == 'image' else None
            }]
            save_session_data(session_id, {"check_queries": json.dumps(obj), "company_id": company_id})
            
        else:
            # Load history from session data
            logger.debug("Adding new query to existing CRM FAQ session")
            queries = json.loads(session_data.get("check_queries", "[]"))
            queries.append({
                "query": query,
                "index": query_uuid,
                # attach image extracted info for merging (None for non-image)
                "extracted_info": extracted_info_for_queue if payload.input_mode == 'image' else None
            })
            query = queries[0].get("query", "") if len(queries) > 0 else query
            session_data["check_queries"] = json.dumps(queries)
            session_data["company_id"] = company_id
            save_session_data(session_id, session_data)
        
        # Check for multiple queries and wait if necessary
        logger.info(f"Checking for multiple queries before executing CRM FAQ agent for session: {session_id}")
        can_proceed = await wait_for_single_query(session_id, query_uuid)
        
        if not can_proceed:
            logger.warning(f"Timeout waiting for single query - proceeding with CRM FAQ execution anyway")
        session_data = get_session_data(session_id)
        queries = json.loads(session_data["check_queries"])
        if len(queries) <= 0:
            logger.info(f"No queries found in CRM FAQ session (expected after merge): {session_id}")
            logger.debug(f"returning response status code 204 for CRM FAQ agent")
            return Response(status_code=204)
        query = queries[0].get("query", "") if len(queries) > 0 else query
        logger.debug(f"CRM FAQ query: {query}")
        
        # If image info is available, embed it into query
        query_for_crm_agent = query
        if extracted_info_from_image:
            query_for_crm_agent = (
                f"This content was extracted from the uploaded image: {extracted_info_from_image} "
                f"and this is the user's query: {query}"
            )
        
        # Invoke CRM FAQ agent with profile information and extracted info
        answer, invocation_id = await invoke_crm_faq_agent(
            query_for_crm_agent, 
            payload.session_id, 
            profile_info=profile_info
        )
        
        # Check if multiple queries exist for consolidation
        session_data = get_session_data(session_id)
        queries = json.loads(session_data["check_queries"])
        if len(queries) > 1:
            # Merge ALL queries into a single consolidated query
            all_query_texts = []
            for i, q in enumerate(queries):
                base_text = (q.get('query') or '').strip()
                image_info = q.get('extracted_info')
                if image_info:
                    merged_part = f"This content was extracted from the uploaded image: {image_info} and this is the user's query: {base_text}"
                else:
                    merged_part = base_text
                if merged_part:
                    all_query_texts.append(merged_part)
            
            # Create merged query - join with space, or structure as numbered list if many queries
            if len(all_query_texts) <= 3:
                new_merged_query = " ".join(all_query_texts)
            else:
                # For many queries, structure as numbered list for clarity
                numbered_queries = [f"{i+1}. {q}" for i, q in enumerate(all_query_texts)]
                new_merged_query = "I have multiple questions: " + " ".join(numbered_queries)
            
            logger.info(f"Merging {len(queries)} CRM FAQ queries into: '{new_merged_query[:100]}...'")
            
            # Keep the structure similar - update the last query in the list with merged content
            queries[-1]["query"] = new_merged_query
            # Clear extracted_info to avoid double-wrapping in future merges
            if 'extracted_info' in queries[-1]:
                queries[-1].pop('extracted_info', None)
            logger.debug(f"Merged {len(queries)-1} CRM FAQ queries into final query")
            
            # Delete events using invocation_id (same as triage agent)
            logger.debug(f"deleting CRM FAQ session events using invocation_id: {invocation_id}")
            if invocation_id:
                delete_events = await remove_conversation_by_invocation_id(
                    session_id, session_id, invocation_id, app_name  # Note: using session_id as user_id for CRM FAQ
                )
                if delete_events["status"] == "success":
                    logger.debug(f"CRM FAQ events successfully deleted using invocation_id")
                else:
                    logger.error(f"failed to delete CRM FAQ events using invocation_id: {delete_events}")
            else:
                logger.warning("No invocation_id available for CRM FAQ event deletion")
            
            # Remove all queries except the last one (which now contains the merged query)
            queries = [queries[-1]]
            
            logger.info(f"After merging: {len(queries)} CRM FAQ query remaining with consolidated content")
            
            # Save the updated queries back to Redis
            session_data["check_queries"] = json.dumps(queries)
            save_session_data(session_id, session_data)
            logger.debug(f"returning response status code 204 for CRM FAQ agent")
            return Response(status_code=204)
        elif len(queries) == 1:
            # Single query - clear the queue and return success
            new_query = queries[0].get("query", "")
            session_data["check_queries"] = json.dumps([])
            save_session_data(session_id, session_data)
            return {
                "status": "success", 
                "query": new_query,  # Return original query, not the modified one
                "answer": answer, 
                "session_id": payload.session_id
            }
        else:
            logger.info(f"No queries found in CRM FAQ session (expected after processing): {session_id}")
            logger.debug(f"returning response status code 204 for CRM FAQ agent")
            return Response(status_code=204)
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error in CRM FAQ agent: {e}", exc_info=True)
        # Attempt to remove the current (failed) query from Redis so that it does not block the queue
        try:
            session_data = get_session_data(session_id)
            if session_data and "check_queries" in session_data:
                queries = json.loads(session_data["check_queries"])
                # If the first query corresponds to the current request (by uuid), remove it
                failed_query_uuid = query_uuid if query_uuid else None
                # Remove the first element if it matches or simply pop index 0 to unblock queue
                query_removed = False
                if failed_query_uuid and queries:
                    if queries[0].get("index") == failed_query_uuid:
                        queries.pop(0)
                        query_removed = True
                    else:
                        # UUID doesn't match, but still pop to avoid blocking
                        queries.pop(0)
                        query_removed = True
                elif queries:
                    # Fallback: always pop index 0 to avoid blocking when no UUID
                    queries.pop(0)
                    query_removed = True
                
                if query_removed:
                    session_data["check_queries"] = json.dumps(queries)
                    save_session_data(session_id, session_data)
                    logger.info(f"Removed failed query from CRM FAQ session {session_id} queue after error.")
        except Exception as cleanup_error:
            logger.error(f"Failed to clean up CRM FAQ queue after error: {cleanup_error}", exc_info=True)
        
        # Extract network details for error email
        network_details = extract_network_details_from_request(request)
        send_exception_email(
            e, 
            f"Error invoking CRM FAQ Agent: {str(e)} | Session ID: {payload.session_id} | Query: {payload.query}", 
            session_id=payload.session_id,
            network_details=network_details
        )
        raise HTTPException(status_code=500, detail="Failed to invoke CRM FAQ Agent")

@app.post("/invoke_crm_analysis")
async def invoke_crm_analysis(
    payload: CRMAnalysisRequest, 
    request: Request,
    crm_analysis_agent_key: str = Depends(authenticate_invoke_kivo_agent),
    network_ctx: NetworkActivityContext = Depends(log_network_activity_dependency)
):
    """
    Generate professional email content for CRM communications.
    
    Processes multimodal messages (text/audio/images) and generates email based on generation_type.
    CRM user sends email to their contact/lead based on received message.
    """
    try:
        logger.info(f"[CRM Analysis] ========== REQUEST STARTED ==========")
        logger.info(f"[CRM Analysis] Received request with generation_type: {payload.generation_type}, company_id: {payload.company_id}")
        logger.info(f"[CRM Analysis] Recipient: {payload.full_name}, Sender: {payload.current_user_name}")
        logger.info(f"[CRM Analysis] User query: {payload.user_query if payload.user_query else 'None'}")
        logger.info(f"[CRM Analysis] Labels: {len(payload.label)} label(s) provided")
        logger.debug(f"[CRM Analysis] Full payload: generation_type={payload.generation_type}, company_id={payload.company_id}, full_name={payload.full_name}, current_user_name={payload.current_user_name}, user_query={payload.user_query}")
        
        # Generate session_id if not provided
        session_id = payload.session_id or str(uuid.uuid4())
        logger.debug(f"[CRM Analysis] Session ID: {session_id} (generated: {not payload.session_id})")
        
        # Convert company_id to int for dynamic agent system
        company_id = int(payload.company_id)
        origin = KIVO_API_BASE_URL
        app_name = "crm_analysis_agent"
        
        logger.debug(f"[CRM Analysis] Configuration - Origin: {origin}, App Name: {app_name}")
        
        # Early validation: Check if LLM credentials exist for this company before processing
        logger.info(f"[CRM Analysis] ========== LLM CREDENTIALS VALIDATION ==========")
        logger.info(f"[CRM Analysis] Validating LLM credentials for company_id: {company_id}, origin: {origin}")
        try:
            custom_model, llm_key, llm_base_url = get_llm_credentials_based_on_company_id(
                app_name=app_name,
                company_id=company_id,
                origin=origin
            )
            logger.info(f"[CRM Analysis] LLM credentials found successfully")
            logger.debug(f"[CRM Analysis] Model: {custom_model}, Base URL: {llm_base_url}")
        except Exception as llm_check_error:
            logger.error(f"[CRM Analysis] LLM credentials validation FAILED: {llm_check_error}")
            raise HTTPException(
                status_code=400,
                detail=f"LLM credentials not configured for company_id: {company_id}, origin: {origin}. Please configure LLM credentials in admin panel before using this endpoint."
            )
        
        # Update network activity context
        network_ctx.set_session_id(session_id)
        network_ctx.set_company_id(str(company_id))
        logger.debug(f"[CRM Analysis] Network context updated with session_id and company_id")
        
        # Process messages to extract text content
        logger.info(f"[CRM Analysis] ========== MESSAGE PROCESSING STARTED ==========")
        logger.info(f"[CRM Analysis] Total messages to process: {len(payload.messages)}")
        processed_messages = []
        
        for idx, message in enumerate(payload.messages):
            message_type = message.message_type
            logger.info(f"[CRM Analysis] Processing message {idx+1}/{len(payload.messages)} - Type: {message_type}")
            
            # Process text content if present
            if message.content and message.content.strip():
                logger.info(f"[CRM Analysis] Message {idx+1}: Found text content")
                logger.debug(f"[CRM Analysis] Message {idx+1}: Content preview: {message.content[:100]}...")
                processed_messages.append(f"[{message_type.upper()} Message]: {message.content}")
                logger.info(f"[CRM Analysis] Message {idx+1}: Text content added successfully")
            
            # Process attachments if present
            if message.attachments and len(message.attachments) > 0:
                logger.info(f"[CRM Analysis] Message {idx+1}: Found {len(message.attachments)} attachment(s)")
                
                for att_idx, attachment in enumerate(message.attachments):
                    attachment_type = attachment.attachment_type.lower()
                    attachment_url = attachment.attachment_url
                    
                    logger.info(f"[CRM Analysis] Message {idx+1}: Processing attachment {att_idx+1}/{len(message.attachments)} - Type: {attachment_type}")
                    logger.debug(f"[CRM Analysis] Message {idx+1}: Attachment {att_idx+1} URL: {attachment_url}")
                    
                    if attachment_type == "image":
                        # Process image using vision API
                        try:
                            logger.info(f"[CRM Analysis] Message {idx+1}: Starting vision API for image {att_idx+1}")
                            vision_request_data = {
                                "query": f"Extract information from this image for {payload.generation_type} email",
                                "session_id": session_id,
                                "user_id": session_id,
                                "origin": origin,
                                "app_name": f"{app_name}_vision_api",
                                "image_url": attachment_url
                            }
                            extracted_content = await handle_vision_api(vision_request_data, origin, company_id)
                            processed_messages.append(f"[Image Attachment {att_idx+1}]: {extracted_content}")
                            logger.info(f"[CRM Analysis] Message {idx+1}: Image {att_idx+1} processed successfully")
                            logger.debug(f"[CRM Analysis] Message {idx+1}: Extracted from image: {extracted_content[:100]}...")
                        except Exception as img_error:
                            logger.error(f"[CRM Analysis] Message {idx+1}: FAILED to process image {att_idx+1}: {img_error}", exc_info=True)
                            processed_messages.append(f"[Image Attachment {att_idx+1}]: (processing failed)")
                            logger.warning(f"[CRM Analysis] Message {idx+1}: Added placeholder for failed image")
                    
                    elif attachment_type == "audio":
                        # Process audio using transcription
                        try:
                            logger.info(f"[CRM Analysis] Message {idx+1}: Starting audio transcription for attachment {att_idx+1}")
                            transcribed_text = await extract_query_from_voice_note(
                                s3_url=attachment_url,
                                company_id=company_id,
                                origin=origin,
                                app_name=f"{app_name}_transcribe"
                            )
                            processed_messages.append(f"[Audio Attachment {att_idx+1}]: {transcribed_text}")
                            logger.info(f"[CRM Analysis] Message {idx+1}: Audio {att_idx+1} transcribed successfully")
                            logger.debug(f"[CRM Analysis] Message {idx+1}: Transcribed audio: {transcribed_text[:100]}...")
                        except Exception as audio_error:
                            logger.error(f"[CRM Analysis] Message {idx+1}: FAILED to transcribe audio {att_idx+1}: {audio_error}", exc_info=True)
                            processed_messages.append(f"[Audio Attachment {att_idx+1}]: (transcription failed)")
                            logger.warning(f"[CRM Analysis] Message {idx+1}: Added placeholder for failed audio")
                    else:
                        logger.warning(f"[CRM Analysis] Message {idx+1}: Unknown attachment type '{attachment_type}', skipping")
            
            if not message.content and not message.attachments:
                logger.warning(f"[CRM Analysis] Message {idx+1}: No content or attachments found, skipping")
        
        logger.info(f"[CRM Analysis] ========== MESSAGE PROCESSING COMPLETED ==========")
        
        # Build final context with user query at the top (highest priority)
        logger.info(f"[CRM Analysis] Building context for email generation...")
        context_parts = []
        
        # 1. USER QUERY FIRST (HIGHEST PRIORITY)
        if payload.user_query and payload.user_query.strip():
            logger.info(f"[CRM Analysis] Adding HIGH PRIORITY user query at top")
            logger.debug(f"[CRM Analysis] User query: {payload.user_query}")
            context_parts.append(f"[USER QUERY/INSTRUCTIONS - HIGH PRIORITY]:\n{payload.user_query}")
            logger.info(f"[CRM Analysis] User query added as highest priority")
        
        # 2. CONTACT LABELS (Context about recipient)
        if payload.label and len(payload.label) > 0:
            logger.info(f"[CRM Analysis] Adding {len(payload.label)} contact label(s)")
            label_info = []
            for label_item in payload.label:
                label_str = f"{label_item.name}: {label_item.description}"
                label_info.append(label_str)
                logger.debug(f"[CRM Analysis] Label added: {label_str}")
            context_parts.append(f"[CONTACT/LEAD LABELS]:\n{', '.join(label_info)}")
            logger.info(f"[CRM Analysis] All labels added successfully")
        
        # 3. MESSAGE HISTORY (Supporting context)
        if processed_messages:
            logger.info(f"[CRM Analysis] Adding {len(processed_messages)} message(s) as supporting context")
            messages_text = "\n\n".join(processed_messages)
            context_parts.append(f"[MESSAGE HISTORY]:\n{messages_text}")
            logger.debug(f"[CRM Analysis] Messages preview: {messages_text[:200]}...")
        
        # Combine all parts with clear separation
        combined_messages = "\n\n" + "="*50 + "\n\n".join(context_parts)
        logger.info(f"[CRM Analysis] Context built with {len(context_parts)} section(s)")
        logger.info(f"[CRM Analysis] Total context length: {len(combined_messages)} characters")
        
        # Validate combined messages
        if not combined_messages.strip():
            logger.error("[CRM Analysis] VALIDATION FAILED: No valid content extracted from messages")
            logger.debug(f"[CRM Analysis] Processed messages count: {len(processed_messages)}")
            raise HTTPException(
                status_code=400,
                detail="No valid content could be extracted from the provided messages"
            )
        
        logger.info(f"[CRM Analysis] Validation passed - content is valid")
        logger.info(f"[CRM Analysis] Final message length: {len(combined_messages)} characters")
        
        # Invoke the CRM analysis agent
        logger.info(f"[CRM Analysis] ========== AGENT INVOCATION STARTED ==========")
        logger.info(f"[CRM Analysis] Agent parameters:")
        logger.info(f"[CRM Analysis]   - generation_type: {payload.generation_type}")
        logger.info(f"[CRM Analysis]   - recipient (full_name): {payload.full_name}")
        logger.info(f"[CRM Analysis]   - sender (current_user_name): {payload.current_user_name}")
        logger.info(f"[CRM Analysis]   - user_query: {payload.user_query if payload.user_query else 'None'}")
        logger.info(f"[CRM Analysis]   - labels_count: {len(payload.label)}")
        logger.info(f"[CRM Analysis]   - session_id: {session_id}")
        logger.info(f"[CRM Analysis]   - company_id: {company_id}")
        logger.debug(f"[CRM Analysis]   - origin: {origin}")
        
        email_data, invocation_id = await invoke_crm_analysis_agent(
            messages_text=combined_messages,
            generation_type=payload.generation_type,
            session_id=session_id,
            company_id=company_id,
            origin=origin,
            full_name=payload.full_name,
            current_user_name=payload.current_user_name
        )
        
        logger.info(f"[CRM Analysis] ========== AGENT INVOCATION COMPLETED ==========")
        logger.info(f"[CRM Analysis] Agent invocation_id: {invocation_id}")
        logger.info(f"[CRM Analysis] Email generated successfully")
        logger.info(f"[CRM Analysis] Email subject: {email_data.get('email_subject')}")
        logger.debug(f"[CRM Analysis] Email body preview: {email_data.get('email_body', '')[:100]}...")
        logger.info(f"[CRM Analysis] Email body length: {len(email_data.get('email_body', ''))} characters")
        
        # Prepare response
        logger.info(f"[CRM Analysis] ========== PREPARING RESPONSE ==========")
        response_data = {
            "status": "success",
            "email_subject": email_data.get("email_subject"),
            "email_body": email_data.get("email_body"),
            "generation_type": payload.generation_type,
            "session_id": session_id
        }

        logger.info(f"[CRM Analysis]------------------------------------------------------------- Response data: {response_data}")

        logger.info(f"[CRM Analysis] Response prepared successfully")
        logger.info(f"[CRM Analysis] ========== REQUEST COMPLETED SUCCESSFULLY ==========")
        
        return response_data
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"[CRM Analysis] Error in CRM analysis endpoint: {e}", exc_info=True)
        
        # Extract network details for error email
        network_details = extract_network_details_from_request(request)
        send_exception_email(
            e,
            f"Error in CRM Analysis: {str(e)} | Generation Type: {payload.generation_type} | Company ID: {payload.company_id}",
            session_id=payload.session_id if payload.session_id else "N/A",
            company_id=payload.company_id,
            network_details=network_details
        )
        raise HTTPException(status_code=500, detail="Failed to generate email content")

from app.routes.iats_sessions import router as iats_router  
app.include_router(iats_router)


@app.post("/chat/remove-conversation-history-from-event")
async def remove_conversation_history_from_event(
    payload: RemoveConversationHistoryRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    base_url: str = Depends(get_base_url_from_request),
    network_ctx: NetworkActivityContext = Depends(log_network_activity_dependency)
):
    """
    Remove iATS conversation history from a specific event for a session.
    
    This endpoint allows users to delete conversation history starting from a
    specific event_id, providing granular control over chat history management.
    
    Args:
        payload (RemoveConversationHistoryRequest): The removal request containing:
            - session_id: Session identifier for the conversation
            - event_id: Event ID from which history will be removed (inclusive)
        credentials (HTTPAuthorizationCredentials): Bearer token for authentication
        base_url (str): Base URL extracted from request for authentication
        
    Returns:
        dict: Removal operation results and status
        
    Raises:
        HTTPException: If authentication fails (403) or removal operation fails
        
    Example:
        ```json
        {
            "status": "success",
            "message": "Conversation history removed successfully",
            "removed_events": 5,
            "session_id": "session_123"
        }
        ```
    """
    
    token = credentials.credentials
    profile_info = await get_current_profile(token, base_url)
    if not profile_info or "email" not in profile_info:
        raise HTTPException(status_code=403, detail="Could not validate user credentials.")
    if not payload.app_name:
        raise HTTPException(status_code=400, detail="app_name is required")
    
    user_id = profile_info["email"]
    
    # Update network activity context
    network_ctx.set_user_id(user_id)
    network_ctx.set_session_id(payload.session_id)
    if profile_info.get('company_id'):
        network_ctx.set_company_id(str(profile_info['company_id']))
    logger.info(f"Request from user {user_id} to remove iATS conversation from event_id {payload.event_id} for session {payload.session_id}")
    result = await remove_conversation_included_from_event(payload.session_id, user_id, payload.event_id, payload.app_name)
    return result

# using origin for validating user profile.
@app.delete("/chat/session/{session_id}")
async def delete_session(
    session_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    origin: str = Depends(get_origin_from_request),
    network_ctx: NetworkActivityContext = Depends(log_network_activity_dependency)
):
    """
    Delete a specific chat session for the authenticated user.
    
    This endpoint permanently removes a chat session and all associated data,
    including conversation history, user interactions, and session metadata.
    
    Args:
        session_id (str): Unique identifier of the session to delete
        credentials (HTTPAuthorizationCredentials): Bearer token for authentication
        origin (str): Origin domain extracted from request headers
        
    Returns:
        dict: Deletion operation results and status
        
    Raises:
        HTTPException: If authentication fails (403) or deletion operation fails (500)
        
    Example:
        ```json
        {
            "status": "success",
            "message": "Session deleted successfully",
            "deleted_session_id": "session_123"
        }
        ```
    """
    logger.debug(f"deleting for origin: {origin}")
    token = credentials.credentials
    profile_info = await get_current_profile(token, origin)
    if not profile_info or "email" not in profile_info:
        raise HTTPException(status_code=403, detail="Could not validate user credentials.")

    user_id = profile_info["email"]
    logger.info(f"User {user_id} requesting to delete session {session_id}")
    
    # Update network activity context
    network_ctx.set_user_id(user_id)
    network_ctx.set_session_id(session_id)
    if profile_info.get('company_id'):
        network_ctx.set_company_id(str(profile_info['company_id']))

    # The service function handles deleting from all relevant tables
    try:
        result = await delete_iats_session(session_id=session_id, user_id=user_id)
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        return result
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete session.")
    

@app.get("/chat/session/{session_id}/history")
async def get_session_history(
    session_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    origin: str = Depends(get_origin_from_request),
    network_ctx: NetworkActivityContext = Depends(log_network_activity_dependency)
):
    """
    Retrieve paginated chat history for a specific session.
    
    This endpoint fetches the conversation history for a given session,
    with support for pagination to handle large conversation histories
    efficiently.
    
    Args:
        session_id (str): Unique identifier of the session
        credentials (HTTPAuthorizationCredentials): Bearer token for authentication
        db (Session): Database session for data access
        page (int): Page number for pagination (minimum: 1)
        limit (int): Number of history items per page (minimum: 1, maximum: 100)
        origin (str): Origin domain extracted from request headers
        
    Returns:
        dict: Paginated chat history with metadata
        
    Raises:
        HTTPException: If authentication fails (403) or history retrieval fails (500)
        
    Example:
        ```json
        {
            "session_id": "session_123",
            "page": 1,
            "limit": 20,
            "total": 45,
            "history": [
                {
                    "event_id": "event_1",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "message": "User query...",
                    "response": "Agent response..."
                }
            ]
        }
        ```
    """
    logger.info(f"Fetching history for session {session_id}, page: {page}, limit: {limit}")
    token = credentials.credentials
    profile_info = await get_current_profile(token, origin)
    if not profile_info or "email" not in profile_info:
        raise HTTPException(status_code=403, detail="Could not validate user credentials.")
    
    user_id = profile_info.get("email")
    logger.info(f"User {user_id} fetching history for session {session_id}")
    
    # Update network activity context
    network_ctx.set_user_id(user_id)
    network_ctx.set_session_id(session_id)
    if profile_info.get('company_id'):
        network_ctx.set_company_id(str(profile_info['company_id']))
    
    offset = (page - 1) * limit
    
    try:
        history_details = get_user_session_details(
            db=db,
            user_id=user_id,
            session_id=session_id,
            limit=limit,
            offset=offset
        )
        return history_details
    except HTTPException as e:
        # Re-raise exceptions from the service layer (e.g., 404 Not Found)
        raise e
    except Exception as e:
        logger.error(f"Failed to fetch session history for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch session history.")
    

@app.post("/chat/session/process_candidate")
async def process_candidate(payload: CandidateSequentialMatchingRequest, credentials: HTTPAuthorizationCredentials = Depends(security), network_ctx: NetworkActivityContext = Depends(log_network_activity_dependency)
):
    """
    Process candidate sequential matching for job applications.
    
    This endpoint analyzes job applicants using AI-powered matching algorithms,
    evaluating candidates against scoring criteria and matching keywords to
    determine job suitability percentages.
    
    Args:
        payload (CandidateSequentialMatchingRequest): The candidate matching request containing:
            - instructions: Job matching instructions and criteria
            - company_id: Company identifier for credential lookup
            - origin: Origin domain for authentication
        credentials (HTTPAuthorizationCredentials): Bearer token for authentication
        
    Returns:
        JSONResponse: Candidate matching results with scores and reasoning
        
    Raises:
        HTTPException: If authentication fails (403) or processing fails (500)
        
    Example:
        ```json
        {
            "status": "success",
            "event": {
                "job_applicant_id": 102,
                "job_matching_percentage": 75.5,
                "job_matching_percentage_reason": "Strong technical skills match, relevant experience in 3 areas..."
            }
        }
        ```
    """
    try:
        logger.info("Invoking candidate sequential matching request")

        token = credentials.credentials
        profile_info = await get_current_profile(token, BASE_URL)

        origin = payload.origin.rstrip(" \\")
        logger.info(f"request received from origin: {origin}")

        if not origin:
            raise HTTPException(status_code=302, detail="Could not find origin.")

        if profile_info:
            logger.info(f"Processing sequential matching for {profile_info.get('email')}")
        if not profile_info:
            raise HTTPException(status_code=403, detail="Could not validate user credentials.")
        
        # Update network activity context
        network_ctx.set_user_id(profile_info.get('email', ''))
        network_ctx.set_company_id(str(payload.company_id))
    
        model, batch_process_llm_key, batch_process_base_url = get_llm_credentials_based_on_company_id("batch_process", payload.company_id, origin)
        logger.info(f"batch_process_base_url {batch_process_base_url}")

        client = OpenAI(api_key=batch_process_llm_key, base_url = batch_process_base_url)
        system_prompt = f"""
        You are a resume matching assistant. You will get job_applicant_id, job_applicant_resume_extracted_text, scoring_criteria, matching_criteria in input.
        Example of input:
        `
        {{
        "job_applicant_id": 102,
        "job_applicant_resume_extracted_text": "Skilled in JavaScript and frontend development. No experience in Python or Django."
        "scoring_criteria":
        "matching_criteria":
        }} 
        `
        For each provided applicant's extracted resume data, use the given scoring criteria and matching keywords to calculate:
        - job_matching_percentage (float): It means how much percent candidate is appropiate for particular job role.
        - job_matching_percentage_reason (string explaining how the score was calculated, breaking down keywords, title, and profile).

        Rules for output:
        1. Output needs to be *strictly* in provided format — no extra text before or after the JSON output.
        2. *Strict*: Always return a float value for `job_matching_percentage` (e.g., 0.0). Never include commas, quotes, or formatting symbols — only numbers.
        3. job_matching_percentage_reason need to be within a max word limit is 50 words.
        4. You must always respond in plain english (UK), donot use any other language in your response.

        **Output JSON format:**
        {{
            "job_applicant_id": ...,
            "job_matching_percentage": ...,
            "job_matching_percentage_reason": "..."
        }}

        **Example Output:**
        Example 1:
        {{
        
            "job_applicant_id": 2,
            "job_matching_percentage": 0,
            "job_matching_percentage_reason": "Did not meet experience criterion, job title mismatch, and did not match any backend-related keywords. 0 + 0 + 0 = 0."
        
        }}

        Example 2:
        
        {{
            "job_applicant_id": 3,
            "job_matching_percentage": 46.7,
            "job_matching_percentage_reason": "Matched Python and REST APIs (but missing Django), partial profile match (missing education), job title partially matches. 40 + 6.7 + 0 = 46.7."
        }}
        
        
        """
        logger.info(f"Using model for batch process {model}")
        response = client.responses.parse(
            model=model,
            temperature=0,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": str(payload.instructions)},
            ],
            text_format=SequentialCompletionOutput,
        )

        return JSONResponse(
            content={"status": "success", "event": response.output_parsed.model_dump()},
            status_code=200
        )

    except Exception as e:
        logger.error(f"Error during candidate matching: {str(e)}", exc_info=True)
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )


@app.post("/upload-image")
async def upload_image(
    images: List[UploadFile] = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = None,
    network_ctx: NetworkActivityContext = Depends(log_network_activity_dependency)
):
    """
    API endpoint to upload multiple image files to S3.
    Accepts multiple image files via multipart/form-data and returns S3 URLs for each.
    Requires Bearer token authentication.
    """
    temp_file_paths = []
    uploaded_images = []
    failed_uploads = []
    
    try:
        # Log the successful authentication
        logger.info(f"Successfully authenticated user with token for image upload")
        
        # Validate that files were uploaded
        if not images or len(images) == 0:
            logger.error("No image files provided in the request")
            return JSONResponse(
                content={
                    "status": "error",
                    "message": "No image files provided in the request"
                },
                status_code=400
            )
        
        # Log the number of images received
        logger.info(f"Received {len(images)} images for upload")
        
        # Create a temporary directory for storing the uploaded images temporarily
        upload_dir = Path("temp_uploads")
        upload_dir.mkdir(exist_ok=True)
        
        # Process each image
        for idx, image in enumerate(images):
            temp_file_path = None
            try:
                # Validate image file
                if not image.filename:
                    failed_uploads.append({
                        "index": idx,
                        "filename": "unknown",
                        "error": "No filename provided"
                    })
                    continue
                
                # Log the image details
                logger.info(f"Processing image {idx + 1}/{len(images)}: filename={image.filename}, content_type={image.content_type}")
                
                # Generate a unique filename for temporary storage
                file_id = uuid.uuid4().hex
                file_extension = Path(image.filename).suffix if image.filename else '.jpg'
                temp_filename = f"upload_{file_id}{file_extension}"
                temp_file_path = upload_dir / temp_filename
                temp_file_paths.append(temp_file_path)
                
                # Save the uploaded file temporarily
                with open(temp_file_path, "wb") as buffer:
                    shutil.copyfileobj(image.file, buffer)
                
                logger.info(f"Image {idx + 1} successfully saved to temporary location: {temp_file_path}")
                
                # Validate and process image (includes compression if needed)
                is_valid, validation_error, processed_file_path = image_validator.validate_and_process_image(
                    str(temp_file_path), 
                    image.content_type, 
                    image.filename
                )
                
                if not is_valid:
                    logger.error(f"Image validation failed for {image.filename}: {validation_error}")
                    failed_uploads.append({
                        "index": idx,
                        "filename": image.filename,
                        "error": validation_error
                    })
                    continue
                
                # Add processed file to cleanup list if it's different from original
                if processed_file_path != str(temp_file_path):
                    temp_file_paths.append(Path(processed_file_path))
                
                # Upload the processed image to S3
                s3_url = s3_service.upload_image(processed_file_path, folder="uploads")
                
                # Get file size for response (use processed file size)
                file_size = Path(processed_file_path).stat().st_size
                
                file_info = {
                    "index": idx,
                    "file_id": file_id,
                    "filename": image.filename,
                    "content_type": image.content_type,
                    "s3_url": s3_url,
                    "size_bytes": file_size
                }
                
                uploaded_images.append(file_info)
                logger.info(f"Image {idx + 1} uploaded to S3 successfully: {s3_url}")
                
            except Exception as upload_error:
                logger.error(f"Error uploading image {idx + 1} ({image.filename if image.filename else 'unknown'}): {str(upload_error)}")
                failed_uploads.append({
                    "index": idx,
                    "filename": image.filename if image.filename else "unknown",
                    "error": str(upload_error)
                })
        
        # Prepare response
        total_images = len(images)
        successful_uploads = len(uploaded_images)
        failed_count = len(failed_uploads)
        
        if successful_uploads == 0:
            # All uploads failed - include specific error messages in main message
            error_messages = [f"{fail['filename']}: {fail['error']}" for fail in failed_uploads]
            main_message = "Image upload failed: " + "; ".join(error_messages)
            return JSONResponse(
                content={
                    "status": "error",
                    "message": main_message,
                    "total_images": total_images,
                    "successful_uploads": 0,
                    "failed_uploads": failed_count,
                    "failed_details": failed_uploads
                },
                status_code=400
            )
        elif failed_count == 0:
            # All uploads successful
            return JSONResponse(
                content={
                    "status": "success",
                    "message": f"All {successful_uploads} images uploaded successfully to S3",
                    "total_images": total_images,
                    "successful_uploads": successful_uploads,
                    "failed_uploads": 0,
                    "data": uploaded_images
                },
                status_code=200
            )
        else:
            # Partial success - include specific error messages for failed uploads
            error_messages = [f"{fail['filename']}: {fail['error']}" for fail in failed_uploads]
            main_message = f"{successful_uploads} of {total_images} images uploaded successfully. Failed uploads: " + "; ".join(error_messages)
            return JSONResponse(
                content={
                    "status": "partial_success",
                    "message": main_message,
                    "total_images": total_images,
                    "successful_uploads": successful_uploads,
                    "failed_uploads": failed_count,
                    "data": uploaded_images,
                    "failed_details": failed_uploads
                },
                status_code=200
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        error_message = f"Internal server error during image upload: {str(e)}"
        logger.error(f"Unexpected error during image upload: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status": "error", 
                "message": error_message
            },
            status_code=500
        )
    finally:
        # Clean up all temporary files
        for temp_file_path in temp_file_paths:
            if temp_file_path and temp_file_path.exists():
                try:
                    temp_file_path.unlink()
                    logger.info(f"Cleaned up temporary file: {temp_file_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up temporary file {temp_file_path}: {str(cleanup_error)}")

@app.post("/delete-image")
async def delete_image(request: Request, network_ctx: NetworkActivityContext = Depends(log_network_activity_dependency)):
    """
    Delete an image from S3 given its URL.
    Expects JSON body: { "url": "<s3_image_url>" }
    """
    try:
        data = await request.json()
        image_url = data.get("url")
        if not image_url:
            return JSONResponse(
                content={"status": "error", "message": "Missing 'url' in request body"},
                status_code=400
            )
        from app.services.s3_service import S3Service
        s3_service = S3Service()
        success = s3_service.delete_file(image_url)
        if success:
            return JSONResponse(
                content={"status": "success", "message": "Image deleted successfully"},
                status_code=200
            )
        else:
            return JSONResponse(
                content={"status": "error", "message": "Failed to delete image"},
                status_code=500
            )
    except Exception as e:
        logger.error(f"Error deleting image: {str(e)}", exc_info=True)
        return JSONResponse(
            content={"status": "error", "message": "Internal server error during image deletion"},
            status_code=500
        )



# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
