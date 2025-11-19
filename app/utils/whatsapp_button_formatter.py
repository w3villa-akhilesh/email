import re
from typing import List, Optional, Dict
from typing import Literal
from pydantic import BaseModel
from openai import OpenAI
from app.services.llm_engine import get_llm_credentials_based_on_company_id
from app.utils.logger import logger
from app.services.my_sql_client import get_db

# for deciding button id
def _slugify_id(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    if not slug:
        slug = "option"
    return f"{slug}-button"

# for title of button
def _truncate_title(title: str, max_len: int = 20) -> str:
    title = title.strip()
    if len(title) <= max_len:
        return title
    return title[: max_len - 1] + "…"
 
# button structure (a type of button schema)
class ButtonSpec(BaseModel):
    title: str
    id: Optional[str] = None
    type: Literal["reply"] = "reply"

# whatsapp message structure (a type of messageschema)
class WhatsAppActionPlan(BaseModel):
    add_buttons: bool
    body_text: Optional[str] = None
    footer_text: Optional[str] = None
    buttons: List[ButtonSpec] = []

# for removing confirmation tag from the text
def _strip_trailing_confirmation_tag(text: str) -> str:
    """
    Remove a trailing <confirmation> tag only if it appears at the very end
    (ignoring whitespace and trailing punctuation such as a final period).
    Do not alter occurrences in the middle of the text.
    """
    if not isinstance(text, str):
        return ""
    # Allow optional trailing whitespace and an optional final period before end of string
    return re.sub(r"\s*<confirmation>\s*\.?\s*$", "", text, flags=re.IGNORECASE)


def _llm_decide_buttons(final_text: str, user_query: str, origin: Optional[str], company_id: Optional[str], app_name: str = "triage_agent", is_confirmation: bool = False) -> Optional[WhatsAppActionPlan]:
    try:
        # Use whatsapp_button_formatter_agent instead of hardcoded name
        whatsapp_agent_name = "whatsapp_formatter_agent"
        
        # Check if agent is enabled for this company
        try:
            logger.info(f"whatsapp_agent_name:---------------------- {whatsapp_agent_name}, company_id: {company_id}, origin: {origin}")
            model, llm_key, llm_base_url = get_llm_credentials_based_on_company_id(whatsapp_agent_name, company_id, origin)
            logger.info(f"model:---------------------- {model}, llm_key: {llm_key}, llm_base_url: {llm_base_url}")
        except Exception as e:
            logger.info(f"WhatsApp button formatter agent not enabled for company {company_id}: {e}")
            return None
        
        if not model or not llm_key or not llm_base_url:
            logger.info(f"WhatsApp button formatter agent not configured for company {company_id}; skipping button formatting")
            return None
            
        if isinstance(model, str) and "openai/" in model:
            model = model.split("openai/")[1]

        if not llm_key:
            logger.warning("LLM key not found for WhatsApp button planner; skipping LLM step")
            return None

        client = OpenAI(api_key=llm_key, base_url=llm_base_url)

        system_instr = (
            "You are a WhatsApp UI action planner. The response contains a confirmation tag, which means the user needs to make a yes/no decision. "
                "Generate exactly 2 buttons: 'Yes' and 'No' for the user to confirm or decline. "
                "Keep the labels simple and clear."
        )

        user_block = f"""
            <assistant_final_reply>
            {final_text}
            </assistant_final_reply>

            <user_query>
            {user_query}
            </user_query>
        """

        resp = client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": system_instr},
                {"role": "user", "content": user_block},
            ],
            text_format=WhatsAppActionPlan,
        )

        plan = resp.output_parsed
        if not isinstance(plan, WhatsAppActionPlan):
            return None
        return plan
    except Exception as e:
        logger.error(f"LLM decision for WhatsApp buttons failed: {e}", exc_info=True)
        return None


def build_whatsapp_interactive(final_text: str, user_query: Optional[str] = None, origin: Optional[str] = None, company_id: Optional[str] = None, app_name: str = "triage_agent", is_confirmation: bool = False) -> Optional[Dict[str, object]]:
    """
    Analyze the final response text and, when applicable, return a WhatsApp
    Interactive Buttons payload structure. Returns None if no buttons apply.
    
    Args:
        final_text: The assistant's final response text
        user_query: The user's original query
        origin: The origin of the request
        company_id: The company ID
        app_name: The app namespace for LLM credentials (e.g., 'user_agent' or 'triage_agent')
        is_confirmation: Whether this is a confirmation (yes/no) interaction
    
    Returns:
        WhatsApp interactive message payload or None
    """
    if not isinstance(final_text, str):
        final_text = ""
    if not isinstance(user_query, str):
        user_query = ""


    # Prefer analyzing the assistant's final text; if generic, also consider the user's query

    # 0) Try LLM-backed decision first
    try:
        plan = _llm_decide_buttons(final_text, user_query, origin, company_id, app_name, is_confirmation)
    except Exception as e:
        logger.warning(f"LLM button plan failed; skipping buttons: {e}", exc_info=True)
        plan = None

    # Build from LLM plan if it recommends buttons
    if plan and plan.add_buttons and plan.buttons:
        chosen = []
        for b in plan.buttons[:3]:
            title = _truncate_title((b.title or "").strip()) if b.title else ""
            if not title:
                continue
            btn_id = b.id or _slugify_id(title)
            chosen.append({
                "type": "reply",
                "reply": {"id": btn_id, "title": title}
            })
        if chosen:
            # For confirmation flows, always use the full assistant response as body
            # instead of an LLM-suggested summary, so users see the complete message.
            if is_confirmation:
                body_text = (final_text or user_query).strip()
                # Only remove the trailing confirmation tag if it appears at the end
                body_text = _strip_trailing_confirmation_tag(body_text)
            else:
                body_text = (plan.body_text or final_text or user_query).strip()
            if len(body_text) > 1000:
                body_text = body_text[:997] + "…"
            footer_text = (plan.footer_text or "Select an option").strip()
            return {
                "body": {"text": body_text},
                "footer": {"text": footer_text},
                "action": {"buttons": chosen},
            }

    return None


def process_whatsapp_response(
    response: str,
    query: str,
    mode: Optional[str],
    origin: Optional[str],
    company_id: Optional[str],
    app_name: str
) -> Optional[Dict[str, object]]:
    """
    Process a response and determine if WhatsApp interactive buttons should be added.
    
    This is the main entry point for WhatsApp button formatting logic. It checks if:
    1. The mode is 'whatsapp'
    2. The response contains a <confirmation> tag
    3. If both conditions are met, it builds and returns the interactive message payload
    
    Args:
        response: The assistant's response text
        query: The user's original query
        mode: The mode of communication (e.g., 'whatsapp')
        origin: The origin of the request
        company_id: The company ID
        app_name: The app namespace for LLM credentials (e.g., 'user_agent' or 'triage_agent')
    
    Returns:
        WhatsApp interactive message payload or None if conditions aren't met
    """
    try:
        # Check if response contains <confirmation> tag using regex
        has_confirmation = bool(re.search(r'<confirmation>', response, re.IGNORECASE))
        
        if not has_confirmation:
            logger.debug(f"No confirmation tag found in response, skipping WhatsApp interactive buttons")
            return None
        
        # Both conditions met - build interactive buttons
        logger.info(f"Confirmation tag detected in response, building WhatsApp interactive buttons (Yes/No)")
        interactive = build_whatsapp_interactive(
            response, 
            query, 
            origin=origin, 
            company_id=company_id, 
            app_name=app_name,
            is_confirmation=True
        )
        
        if interactive:
            logger.info(f"Successfully built WhatsApp interactive message with buttons")
        else:
            logger.warning(f"build_whatsapp_interactive returned None despite confirmation tag")
        
        return interactive
        
    except Exception as e:
        logger.error(f"Failed to process WhatsApp response: {e}", exc_info=True)
        return None

#cleanup function for removing tag from the response
def remove_tags(response : str) -> str:
    removable_tags = ["confirmation"]
    try:
        if isinstance(response, str):
            for _tag in removable_tags:
                # remove <confirmation>  ,  </confirmation>  ,  <confirmation />
                response = re.sub(rf"</?{_tag}\s*/?>", "", response, flags=re.IGNORECASE)

            response = response.strip()
            return response
    except Exception:
        pass
    return response


__all__ = ["build_whatsapp_interactive", "process_whatsapp_response", "remove_tags"]


