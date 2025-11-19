import os
from app.services.mcp_connection import connect_to_mcp_server
from app.utils.logger import logger
from google.adk.agents.llm_agent import LlmAgent
from app.services.llm_engine import get_llm_engine
from app.core.constants import CRM_FAQ_AGENT_URL
from app.services.redis_common_state import get_session_data, save_session_data
from app.services.crm_current_user_info import get_crm_current_profile, get_crm_profile_block
from app.services.lifecycle_hooks import save_data_in_crm_context, after_agent_invocation_callback_context, simple_before_tool_modifier, simple_after_tool_modifier
from google.adk.agents.callback_context import CallbackContext
import json
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from app.services.my_sql_client import create_db_url
from google.genai import types
from app.models.schema import balanced_generation_config
from app.helpers.BaseAgent import Kivo_LLMAgent
from app.services.agent_prompt_service import agent_prompt_service

async def initiate_crm_faq_agent(session_id: str, company_id: int, app_name: str, origin: str, profile_block=None, preloaded_context=None, mode="web"):
    crm_faq_toolset = None
    try:
        logger.info("Initializing CRM FAQ Agent")
        
        # Connect to CRM FAQ MCP server
        logger.debug("Initiating CRM FAQ MCP tool connection...")
        agent_type = None
        crm_faq_toolset = await connect_to_mcp_server(CRM_FAQ_AGENT_URL,None,agent_type,[],[],session_id)
        if not crm_faq_toolset:
            error_msg = "Failed to connect to CRM FAISS MCP server or no tools available."
            logger.error(error_msg)
            raise ConnectionError(error_msg)

        logger.info("Setting up crm_faq_agent")
        
        # Get LLM engine for the agent dynamically
        crm_faq_model = get_llm_engine(agent_name='crm_faq_agent', company_id=company_id)

        # Get dynamic instructions for CRM FAQ agent
        crm_faq_agent_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="crm_faq_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=profile_block,
            preloaded_context=preloaded_context,
            mode=mode
        )

        crm_faq_agent = Kivo_LLMAgent(
            name="crm_faq_agent",
            model=crm_faq_model,
            instruction=crm_faq_agent_instructions,
            description=agent_prompt_service.get_agent_description("crm_faq_agent", company_id),
            output_key="crm_faq_response",
            tools=crm_faq_toolset,
            # before_agent_callback=load_crm_context,
            # after_agent_callback=after_agent_invocation_callback_context,
            # before_tool_callback=simple_before_tool_modifier,
            # after_tool_callback=simple_after_tool_modifier,
            generate_content_config=balanced_generation_config
        )
        return crm_faq_agent

    except Exception as e:
        logger.error(f"Error in initiate_crm_faq_agent: {e}", exc_info=True)
        raise

    finally:
        if crm_faq_toolset:
            try:
                # crm_faq_toolset is a list of tools, not a toolset object with close method
                # No need to close individual tools as they are managed by the MCP connection
                pass
            except Exception as e:
                logger.warning(f"Toolset close error: {e}", exc_info=True)

async def invoke_crm_faq_agent(query: str, session_id: str, profile_info: dict = None):
    try:
        logger.debug(f"Invoking crm_faq_agent with query: {query}, session_id: {session_id}")

        # Extract company_id from profile_info or use default
        company_id = profile_info.get('company_id') if profile_info else int(os.getenv("ACCOUNT_ID"))
        app_name = "crm_faq_agent"
        origin = "crm"  # Default origin for CRM FAQ agent
        
        # Create profile block for personalization
        profile_block = ""
        if profile_info:
            profile_block, user_email = get_crm_profile_block(profile_info)

        # Initialize the agent with dynamic parameters
        agent = await initiate_crm_faq_agent(
            session_id=session_id, 
            company_id=company_id,
            app_name=app_name,
            origin=origin,
            profile_block=profile_block,
            preloaded_context=None,
            mode="web"
        )

        # Prepare user input
        llm_query_json = {
            "query": query,
        }
        content = types.Content(role="user", parts=[types.Part(text=json.dumps(llm_query_json, indent=2))])

        # Create DB session
        db_url = create_db_url()
        if not db_url:
            error_msg = "Invalid database URL"
            logger.error(error_msg)
            raise ValueError(error_msg)

        session_service = DatabaseSessionService(db_url=db_url)
        session = await session_service.get_session(app_name=app_name, user_id=session_id, session_id=session_id)
        if not session:
            session = await session_service.create_session(
                app_name=app_name,
                user_id=session_id,
                session_id=session_id
            )

        # Run the agent
        runner = Runner(agent=agent, app_name=app_name, session_service=session_service)
        response = None
        invocation_id = None
        async for event in runner.run_async(user_id=session_id, session_id=session_id, new_message=content):
            invocation_id = event.invocation_id
            if event.is_final_response():
                logger.info("Final response received from the agent.")
                if event.content is None or not hasattr(event.content, "parts") or not event.content.parts:
                    logger.warning("First event has no content, continuing to wait for valid response...")
                    continue
                else:
                    response = event.content.parts[0].text
                    logger.debug(f"Agent response: {response}")
                    break

        # Fallback if no response was set
        if response is None:
            error_msg = "No final response received from the agent"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Parse response
        try:
            answer = json.loads(response)
        except json.JSONDecodeError:
            answer = response

        return answer, invocation_id
        
    except Exception as e:
        logger.error(f"Error in invoke_crm_faq_agent: {e}", exc_info=True)
        raise 
