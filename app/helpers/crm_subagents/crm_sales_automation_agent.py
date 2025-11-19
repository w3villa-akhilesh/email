import time
from typing import Any, Dict, Optional
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
from app.utils.prompt import CRM_SALES_AUTOMATION_AGENT_PROMPT
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
from app.core.constants import CRM_SALES_MCP_SERVER_URL


async def initiate_crm_sales_automation_agent(session_id, profile_block, company_id, app_name, origin):
    try:
        logger.debug("initiate CRM Sales Automation mcp tool connection ...")
        crm_sales_toolset = await connect_to_mcp_server(CRM_SALES_MCP_SERVER_URL, None, ['crm_sales'])

        # If MCP server is not available, create agent without tools for testing
        if not crm_sales_toolset:
            logger.warning("CRM Sales Automation MCP server not available. Creating agent with mock responses for testing.")
            crm_sales_toolset = []  # Empty toolset for now

        logger.info("Setting up CRM Sales Automation Agent")
        model = get_llm_engine(agent_name='CRM_Sales_Automation_Agent', company_id=company_id, app_name=app_name, origin=origin)

        async def load_crm_context(callback_context: CallbackContext):
            return await save_data_in_crm_context(time.time(), profile_block, callback_context)

        agent = LlmAgent(
            name="crm_sales_automation_agent",
            model=model,
            instruction=CRM_SALES_AUTOMATION_AGENT_PROMPT,
            description="A CRM Sales Automation agent that handles routine task automation and process optimization.",
            tools=crm_sales_toolset,
            before_agent_callback=load_crm_context,
            after_agent_callback=after_agent_invocation_callback_context
        )

        logger.info("CRM Sales Automation Agent initialized successfully")
        return agent

    except Exception as e:
        logger.error(f"Error initializing CRM Sales Automation Agent: {e}", exc_info=True)
        return None 