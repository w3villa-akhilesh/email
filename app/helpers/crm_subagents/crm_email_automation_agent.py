from app.services.current_user_info import get_current_profile
from app.services.lifecycle_hooks import before_agent_invocation_callback_context, after_agent_invocation_callback_context, save_data_in_crm_context, simple_after_tool_modifier, simple_before_tool_modifier
from app.services.mcp_connection import connect_to_mcp_server
from app.utils.logger import logger
from google.adk.agents.llm_agent import LlmAgent
from app.services.llm_engine import get_llm_engine
from datetime import datetime
from app.utils.prompt import CRM_EMAIL_AUTOMATION_AGENT_PROMPT
from app.core.constants import CRM_EMAIL_MCP_SERVER_URL
from google.adk.agents.callback_context import CallbackContext
from app.models.schema import strict_generation_config

async def initiate_crm_email_automation_agent(session_id, profile_block, company_id, app_name, origin):
    try:
        logger.debug("initiate CRM Email Automation mcp tool connection ...")
        crm_email_toolset = await connect_to_mcp_server(CRM_EMAIL_MCP_SERVER_URL, None, ['crm_email'])
        
        # If MCP server is not available, create agent without tools for testing
        if not crm_email_toolset:
            logger.warning("CRM Email MCP server not available. Creating agent with mock responses for testing.")
            crm_email_toolset = []  # Empty toolset for now
        
        logger.info("Setting up CRM Email Automation Agent")

        crm_email_agent_model = get_llm_engine('CRM_Email_Automation_Agent', company_id, app_name, origin)

        date = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

        async def load_crm_context(callback_context: CallbackContext):
            return await save_data_in_crm_context(date, profile_block, callback_context)

        kivo_crm_email_agent = LlmAgent(
            name="crm_email_automation_agent",
            model=crm_email_agent_model,
            instruction=CRM_EMAIL_AUTOMATION_AGENT_PROMPT,
            description="Handles queries about email automation, campaigns, follow-ups, and automated communications in CRM.",
            output_key="final_summary",
            tools=crm_email_toolset,
            before_agent_callback=load_crm_context,
            after_agent_callback=after_agent_invocation_callback_context,
            before_tool_callback=simple_before_tool_modifier,
            after_tool_callback=simple_after_tool_modifier,
            generate_content_config=strict_generation_config
        )
        return kivo_crm_email_agent
    except Exception as e:
        logger.error(f"Error in initiate_crm_email_automation_agent: {e}", exc_info=True)
        return None 