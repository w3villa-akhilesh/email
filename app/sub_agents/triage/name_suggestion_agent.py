import os
from dotenv import load_dotenv
import urllib3
from app.services.lifecycle_hooks import after_agent_invocation_callback_context, save_data_in_hrms_context, simple_after_tool_modifier, simple_before_tool_modifier
from app.utils.logger import logger
from google.adk.agents.llm_agent import LlmAgent
from app.services.llm_engine import get_llm_engine
from datetime import datetime
from app.utils.memory_utils import memorize
from app.services.agent_prompt_service import agent_prompt_service
from google.adk.agents.callback_context import CallbackContext
from app.models.schema import strict_generation_config
from elasticsearch import Elasticsearch
from app.services.redis_common_state import get_session_data
from google.adk.tools.tool_context import ToolContext
load_dotenv()


# OPTIONAL: Disable SSL warnings (use only for local testing or self-signed certs)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

VERIFY_CERTS = False

# Override ES connection details as requested
ELASTIC_HOST = os.getenv('ELASTIC_HOST')
ELASTIC_USERNAME = os.getenv('ELASTIC_USERNAME')
ELASTIC_PASSWORD = os.getenv('ELASTIC_PASSWORD')


# === Connect to Elasticsearch ===

es = Elasticsearch(
    ELASTIC_HOST,
    basic_auth=(ELASTIC_USERNAME, ELASTIC_PASSWORD),
    verify_certs=VERIFY_CERTS,
    request_timeout=30
)
logger.debug(f"Elasticsearch client initialized. Host: {ELASTIC_HOST}, verify_certs: {VERIFY_CERTS}")

def get_index_name(company_id):
    return f"vector-embeddings_profile_{company_id}"


async def suggest_similar_names(session_id: str, query: str, tool_context: ToolContext):
    """
    This tool is used to get suggestion for names and to find the best possible name for any particular name.
    Args:
    session_id: Unique identifier for the session.
    query: Query is like name of employee with some criteria like: department, location, contact_number.
    e.g: "Aman from Noida".

    Returns:
    Name of employee with employee_id, location, department and score.
    for e.g: {"name":"Aman Singh", "employee_id": 12345, "location":"Noida", "department":"Engineering", "score": 0.9}
    """
    logger.info(f"Entering suggest_similar_names with name: {query} for session_id: {session_id}")
    try:
        app_name = "triage_agent"
        logger.debug(f"Fetching session data for session_id={session_id}, app_name={app_name}")
        session_data = get_session_data(session_id, app_name)
        logger.debug(f"Session data fetched: {'present' if bool(session_data) else 'absent'}")
        if not session_data:
            return {"message": "Session not found"}
        company_id = session_data.get("company_id")
        logger.debug(f"company_id from session: {company_id}")
        if not company_id:
            logger.debug("Company ID not found in session data.")
            return {"message": "Company ID not found"}

        # Prepare body to mimic the provided curl. If a query is present, use fuzzy match; otherwise match_all.
        if query and str(query).strip():
            search_body = {
                "query": {
                    "match": {
                        "full_name": {
                            "query": query,
                            "fuzziness": "AUTO"
                        }
                    }
                },
                "size": 100
            }
        else:
            search_body = {
                "query": {"match_all": {}},
                "size": 100
            }

        # Make a direct HTTP GET to the Elasticsearch _search API using Basic auth header (as in curl)
        import requests, json
        url = f"{ELASTIC_HOST.rstrip('/')}/profiles_1/_search"
        basic_token = "ZWxhc3RpYzp3M3ZpbGxhZWxhU3RpQzE5MQ=="  # base64('elastic:w3villaelaStiC191')
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {basic_token}",
        }
        logger.debug(f"GET {url} with body: {search_body}")
        http_response = requests.get(
            url,
            data=json.dumps(search_body),
            headers=headers,
            verify=VERIFY_CERTS,
            timeout=30,
        )
        logger.debug(f"HTTP status: {http_response.status_code}")
        if not http_response.ok:
            logger.error(f"Elasticsearch HTTP error: {http_response.status_code} - {http_response.text}")
            return {"message": "Search failed", "status": http_response.status_code}
        response_json = http_response.json()
        logger.debug("Search executed successfully via HTTP GET.")
        hits = response_json.get("hits", {}).get("hits", [])
        logger.debug(f"Number of hits received: {len(hits)}")
        similar_employee_names = [
            {
                "name": hit["_source"].get("full_name", ""),
                "employee_id": hit["_source"].get("id", ""),
                "location": hit["_source"].get("location", ""),
                "department": hit["_source"].get("department", ""),
                "score": hit["_score"]
            }
            for hit in hits
        ]

        logger.info(f"similar names: {similar_employee_names}")
        logger.debug("Updating tool_context.state['profile_list'] with search results")
        tool_context.state["profile_list"] = similar_employee_names 
        logger.debug("tool_context.state updated successfully")
        return similar_employee_names
    except Exception as e:
        logger.error(f"Error in suggest_similar_names: {e}", exc_info=True)
        raise


async def initiate_name_suggestion_agent(session_id, profile_block, company_id, app_name, origin, preloaded_context=None, mode="web"):
    try:
        
        logger.info("Setting up Suggest Similar Names Agent")
        logger.debug(f"Initializing LLM engine for company_id={company_id}, app_name={app_name}, origin={origin}")
        # Use correct agent name for LLM credentials
        name_suggestion_agent_model = get_llm_engine('name_suggestion_agent', company_id, app_name, origin)
        logger.debug("LLM engine initialized successfully")

        date= datetime.today().strftime("%Y-%m-%d %H:%M:%S")
        logger.debug(f"Evaluation date set: {date}")

        async def load_triage_context(callback_context: CallbackContext):
            logger.debug("load_triage_context invoked; saving data in HRMS context")
            result = await save_data_in_hrms_context(date, profile_block, callback_context, preloaded_context)
            logger.debug("Data saved in HRMS context successfully")
            return result

        logger.debug("Constructing LlmAgent for name suggestion")
        
        # Load dynamic instructions and description
        agent_instructions = agent_prompt_service.get_agent_prompt(
            agent_name="name_suggestion_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=profile_block,
            preloaded_context=preloaded_context,
            mode=mode,
            close_match=False  # Default value, will be updated by tool callback
        )
        
        name_suggestion_agent = LlmAgent(
            name="name_suggestion_agent_tool",
            model=name_suggestion_agent_model,
            instruction=agent_instructions,
            description=agent_prompt_service.get_agent_description("name_suggestion_agent", company_id),
            output_key="final_summary",
            tools=[suggest_similar_names,memorize],
            before_agent_callback=load_triage_context, # check before executing agent
            after_agent_callback=after_agent_invocation_callback_context,    # check after executing agent
            before_tool_callback=simple_before_tool_modifier,
            after_tool_callback=simple_after_tool_modifier, # Assign the callback
            generate_content_config=strict_generation_config

        )
        logger.debug("LlmAgent constructed successfully; returning agent instance")
        return name_suggestion_agent  # Return the agent here
    except Exception as e:
        logger.error(f"Error in initiate_name_suggestion_agent: {e}", exc_info=True)
        return None
    
