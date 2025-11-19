import asyncio
import contextlib
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv
from google.genai import types
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from app.utils.logger import logger
from app.services.agent_prompt_service import agent_prompt_service
from app.services.dynamic_prompt_factory import prompt_factory
from app.core.constants import TRANSCRIBE_MCP_SERVER_URL, TRANSCRIBE_AGENT_NAME
from app.services.llm_engine import get_llm_engine
from app.services.transcription import async_download_and_transcribe
from app.services.mcp_connection import connect_to_mcp_server

load_dotenv()

async def initiate_transcribe_agent(origin: str, session_id: str, company_id: int, app_name: str):
    """
    Initializes and returns the transcribe_agent using dynamic prompt factory.
    
    Args:
        origin: Origin URL of the request
        session_id: Session identifier
        company_id: Company identifier
        app_name: Application name
        
    Returns:
        LlmAgent: The initialized transcribe_agent
    """
    try:
        logger.debug("Initiating transcribe_agent...")
        
        # Get the LLM engine for transcribe agent
        transcribe_model = get_llm_engine('transcribe_agent', company_id)
        
        # Get dynamic instructions for transcribe agent using the prompt factory
        transcribe_agent_instructions = prompt_factory.get_dynamic_prompt(
            agent_name="transcribe_agent",
            company_id=company_id,
            # Template variables for transcription (these will be filled from session state)
            transcription_text="{transcription_text}",
            id_type="{id_type}",
            id_value="{id_value}",
            transaction_id="{transaction_id}",
            message_id="{message_id}",
            session_id="{session_id}",
            current_date="{current_date}",
            profile_info="{profile_info}",
            preloaded_context="{preloaded_context}"
        )
        
        # Connect to MCP server for CRM tools
        crm_toolset = await connect_to_mcp_server(TRANSCRIBE_MCP_SERVER_URL, session_id=session_id)
        if not crm_toolset:
            logger.warning("Failed to connect to MCP server, transcribe agent will have limited functionality")
            crm_toolset = []
        
        # Create the transcribe agent
        transcribe_agent = LlmAgent(
            name="transcribe_agent",
            model=transcribe_model,
            instruction=transcribe_agent_instructions,
            description=prompt_factory.get_agent_description("transcribe_agent", company_id),
            tools=crm_toolset,
        )
        
        return transcribe_agent
        
    except Exception as e:
        logger.error(f"Error in initiate_transcribe_agent: {e}", exc_info=True)
        raise

async def process_audio_background(agent_name: str, transaction_id: Optional[str], message_id: Optional[str], s3_url: str, company_id: str, origin: str):
    """Background task to handle transcription, summarization and CRM update."""
    try:
        logger.info("Downloading & transcribing audio...")
        # Use async function - it always uses 'transcribe_agent' internally for credentials
        transcription_text = await async_download_and_transcribe(
            s3_url=s3_url,
            company_id=company_id,
            app_name=agent_name,
            origin=origin
        )
        if not transcription_text:
            logger.error("Transcription failed or returned empty text.")
            return

        logger.debug("-" * 100 + f"\nTRANSCRIPTION RESULT --->\n{transcription_text}\n" + "-" * 100)

        logger.debug("Initializing transcribe agent using dynamic factory...")
        
        # Use the new dynamic agent initialization
        agent = await initiate_transcribe_agent(
            origin=origin,
            session_id="transcribe_session",  # Default session for background process
            company_id=int(company_id),
            app_name=agent_name
        )

        if message_id is not None:
            id_type, id_value = "message_id", message_id
        elif transaction_id is not None:
            id_type, id_value = "transaction_id", transaction_id
        else:
            # Fallback if neither is provided (should not happen in normal flow)
            id_type, id_value = "message_id", "unknown"
            logger.warning("Neither transaction_id nor message_id provided")

        session_service = InMemorySessionService()
        session = await session_service.create_session(
            state={
                "transcription_text": transcription_text,
                "id_type": id_type,
                "id_value": id_value,
                "message_id": message_id,
                "transaction_id": transaction_id,
               "session_id": "transcribe_session",
                "current_date": datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
                "profile_info": "",
                "preloaded_context": ""
            },
            app_name=agent_name,
            user_id="user_fs"
        )

        runner = Runner(app_name=agent_name, agent=agent, session_service=session_service)

        query = (
            f"Summarize the following call transcription:\n\n{transcription_text}\n\n"
            f"Classify the lead, and then call the MCP tool `send_transcription_to_crm` "
            f"with the payload format and necessary arguments as per your instructions."
        )
        content = types.Content(role="user", parts=[types.Part(text=query)])

        events_async = runner.run_async(
            session_id=session.id,
            user_id=session.user_id,
            new_message=content
        )

        async for event in events_async:
            for part in event.content.parts:
                if part.text:
                    logger.debug("-" * 100 + f"\nRESULTS---> \n{part.text}\n" + "-" * 100)

    except Exception as e:
        logger.error(f"Background processing failed: {e}", exc_info=True)

    finally:
        # Cleanup is now handled within the agent lifecycle
        logger.debug("Transcribe agent background processing completed.")


async def invoke_transcribe_agent(agent_name: str, transaction_id: Optional[str], message_id: Optional[str], s3_url: str, company_id: str, origin: str):
    """
    Immediately return audio_status and run transcription + summary + CRM update in background.
    """
    asyncio.create_task(
        process_audio_background(agent_name, transaction_id, message_id, s3_url, company_id, origin)
    )
    return {"audio_status": True}
