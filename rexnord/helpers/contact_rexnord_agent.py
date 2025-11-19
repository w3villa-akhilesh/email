from rexnord.utils.logger import setup_logger
from google.adk.agents.llm_agent import LlmAgent
# Use main app's dynamic services
from app.services.llm_engine import get_llm_engine
from app.services.agent_prompt_service import agent_prompt_service
from datetime import datetime
from google.adk.agents.callback_context import CallbackContext
from rexnord.services.lifecycle_hooks import (
    after_agent_invocation_callback_context,
    save_data_in_rexnord_context,
    simple_after_tool_modifier,
    simple_before_tool_modifier,
)
from fastapi import HTTPException
from rexnord.models.schema import ResponseFormat, json_response_config
import re

logger = setup_logger("contact_rexnord_agent")

NBSP = "\u00A0"  # Non-breaking space
ZWS = "\u200B"   # Zero-width space


# --- Utility: Strip HTML Tags ---
def _strip_html(text: str) -> str:
    """Remove HTML tags and entities from text."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = (
        text.replace("&nbsp;", " ")
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
    )
    return re.sub(r"[ \t]+", " ", text).strip()


# --- Utility: Normalize WhatsApp / Invisible Characters ---
def _normalize_whatsapp(text: str) -> str:
    """Normalize newlines, spaces, and invisible characters in text."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace(NBSP, " ").replace(ZWS, "")
    text = re.sub(r"[ \t]+(?=\n|$)", "", text)
    return text.strip()


# --- Utility: Combined Field Normalizer ---
def _normalize_field(value: str) -> str:
    """Clean a single text field (HTML + invisible chars)."""
    value = _strip_html(value)
    value = _normalize_whatsapp(value)
    return value.strip()


def find_contact_details(session_id: str) -> dict:
    """
    Fetch and normalize contact details for Rexnord executives.

    Args:
        session_id (str): Unique session identifier for logging/tracking.

    Returns:
        dict: Dictionary containing a list of cleaned contact details,
              including names, emails, and mobile numbers.
    """
    logger.info(f"Session ID: {session_id}")

    raw_contacts = [
        {
            "name": "Ms Jyoti",
            "email": "Sales7@rexnordindia.com",
            "mobile": "9594160859"
        },
        {
            "name": "Ms Manjiri",
            "email": "branding@rexnordindia.com",
            "mobile": "8692076691"
        }
    ]

    # Normalize all string fields for clean, display-safe output
    normalized_contacts = [
        {
            "name": _normalize_field(c.get("name", "")),
            "email": _normalize_field(c.get("email", "")),
            "mobile": _normalize_field(c.get("mobile", "")),
        }
        for c in raw_contacts
    ]

    return {"contacts": normalized_contacts}

async def save_data_in_contact_context(date, profile_block, callback_context: CallbackContext):
    # Reuse triage context saver to store profile and timestamp context
    return await save_data_in_rexnord_context(date, "", "", callback_context)

async def initiate_contact_rexnord_agent(session_id, profile_block, company_id, app_name, origin, mode="web", **kwargs):
    """Initialize contact rexnord agent with dynamic LLM and prompts"""
    toolset = None
    try:
        logger.debug("Initiating Contact Rexnord MCP tool connection ...")
        
        logger.info("Setting up Contact Rexnord Agent")
        # Use dynamic LLM engine with agent name
        rexnord_agent_model = get_llm_engine(agent_name='contact_rexnord_agent', company_id=company_id)

        date = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

        async def load_contact_context(callback_context: CallbackContext):
            return await save_data_in_contact_context(date, profile_block, callback_context)

        # Get dynamic prompt for contact_rexnord_agent
        contact_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="contact_rexnord_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=profile_block,
            mode=mode
        )

        contact_rexnord_agent = LlmAgent(
            name="contact_rexnord_agent",
            model=rexnord_agent_model,
            instruction=contact_instructions,
            description=agent_prompt_service.get_agent_description("contact_rexnord_agent", company_id),
            output_schema=ResponseFormat,
            generate_content_config=json_response_config,
            output_key="final_summary",
            disallow_transfer_to_parent=True,
            disallow_transfer_to_peers=True,
            tools=[find_contact_details],
            before_agent_callback=load_contact_context,
            after_agent_callback=after_agent_invocation_callback_context,
            before_tool_callback=simple_before_tool_modifier,
            after_tool_callback=simple_after_tool_modifier,
        )
        return contact_rexnord_agent
    except Exception as e:
        logger.error(f"Error in initiate_contact_rexnord_agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"contact_rexnord_agent initialization failed: {str(e)}")
    finally:
        if toolset:
            try:
                await toolset.close()
            except Exception as e:
                logger.warning(f"Toolset close error: {e}", exc_info=True)
