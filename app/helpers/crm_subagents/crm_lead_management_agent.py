import time
from typing import Any, Dict, Optional
from datetime import datetime
from app.services.lifecycle_hooks import after_agent_invocation_callback_context
from app.services.my_sql_client import create_db_url
from app.services.profile_block import get_my_profile_block
from app.utils.final_logger import get_final_agent_response
from app.utils.logger import logger
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.genai import types
from app.services.llm_engine import get_llm_engine
import uuid
from app.utils.history import construct_previous_context
from app.utils.prompt import CRM_LEAD_MANAGEMENT_AGENT_PROMPT, GREETING_INSTRUCTIONS
from app.services.current_user_info import get_current_profile
import json
import os
from google.adk.sessions import DatabaseSessionService
from app.core.constants import ALLOWED_CALLING_EMAILS
from pm_board_data.core.config import KIVO_API_BASE_URL
from google.adk.agents.callback_context import CallbackContext
from app.services.lifecycle_hooks import save_data_in_crm_context
from google.adk.events import Event, EventActions
from app.services.mcp_connection import connect_to_mcp_server
from app.core.constants import CRM_LEAD_MCP_SERVER_URL


async def initiate_crm_lead_management_agent(session_id, profile_block, company_id, app_name, origin):
    try:
        logger.debug("initiate CRM Lead Management mcp tool connection ...")
        agent_type = None
        exclude_tool_type = []
        include_tool_type = []
        crm_lead_toolset = await connect_to_mcp_server(CRM_LEAD_MCP_SERVER_URL, None, agent_type, exclude_tool_type, include_tool_type, session_id)

        # If MCP server is not available, create agent without tools for testing
        if not crm_lead_toolset:
            logger.warning("CRM Lead MCP server not available. Creating agent with mock responses for testing.")
            crm_lead_toolset = []  # Empty toolset for now

        logger.info("Setting up CRM Lead Management Agent")
        model = get_llm_engine(agent_name='CRM_Lead_Management_Agent', company_id=company_id, app_name=app_name, origin=origin)

        # Get today's date for date awareness
        today_date = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
        crm_lead_management_agent_instructions = (
            f"{CRM_LEAD_MANAGEMENT_AGENT_PROMPT}\n{GREETING_INSTRUCTIONS}"
        )

        async def load_crm_context(callback_context: CallbackContext):
            return await save_data_in_crm_context(today_date, profile_block, callback_context, session_id)

        agent = LlmAgent(
            name="crm_lead_management_agent",
            model=model,
            instruction=crm_lead_management_agent_instructions,
            description="A CRM Lead Management agent that handles lead lifecycle, scoring, and qualification.",
            tools=crm_lead_toolset,
            before_agent_callback=load_crm_context,
            after_agent_callback=after_agent_invocation_callback_context
        )

        logger.info("CRM Lead Management Agent initialized successfully")
        return agent

    except Exception as e:
        logger.error(f"Error initializing CRM Lead Management Agent: {e}", exc_info=True)
        return None 
