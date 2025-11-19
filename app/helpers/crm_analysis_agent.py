from app.utils.logger import logger
from google.adk.agents.llm_agent import LlmAgent
from app.services.llm_engine import get_llm_engine
from datetime import datetime
from google.genai import types
import json
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from app.services.my_sql_client import create_db_url
from app.models.schema import balanced_generation_config
from app.helpers.BaseAgent import Kivo_LLMAgent
from app.services.dynamic_prompt_factory import prompt_factory

async def initiate_crm_analysis_agent(session_id: str, generation_type: str, company_id: int = None, origin: str = None, full_name: str = None, current_user_name: str = None):
    """
    Initialize the CRM Analysis Agent for generating email content based on generation_type.
    
    Args:
        session_id: Session identifier
        generation_type: Type of email generation (reminder, greet, etc)
        company_id: Company identifier for LLM configuration (int)
        origin: Origin URL for LLM credentials
        full_name: Full name of the recipient for personalized emails
        current_user_name: Name of the current user sending the email
    
    Returns:
        Configured CRM analysis agent
    """
    try:
        logger.info(f"[CRM Analysis Agent] ========== AGENT INITIALIZATION STARTED ==========")
        logger.info(f"[CRM Analysis Agent] Parameters: generation_type={generation_type}, full_name={full_name}")
        logger.info(f"[CRM Analysis Agent] Sender: {current_user_name}")
        logger.debug(f"[CRM Analysis Agent] Session: {session_id}, Company: {company_id}, Origin: {origin}")
        
        agent_name = "crm_analysis_agent"
        logger.debug(f"[CRM Analysis Agent] Agent name: {agent_name}")
        
        # Get LLM model configuration using dynamic system
        logger.info(f"[CRM Analysis Agent] Loading LLM engine configuration...")
        logger.debug(f"[CRM Analysis Agent] LLM params: agent_name='{agent_name}', company_id={company_id}")
        crm_analysis_model = get_llm_engine(agent_name, company_id=company_id)
        logger.info(f"[CRM Analysis Agent] LLM engine loaded successfully: {crm_analysis_model}")
        
        today_date = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
        logger.debug(f"[CRM Analysis Agent] Current date: {today_date}")
        
        # Get dynamic agent instructions using prompt factory
        logger.info(f"[CRM Analysis Agent] Loading dynamic agent instructions prompt...")
        crm_analysis_agent_instructions = prompt_factory.get_dynamic_prompt(
            agent_name=agent_name,
            company_id=company_id,
            current_date="{current_date}",
            generation_type="{generation_type}",
            session_id="{session_id}",
            full_name="{full_name}",
            current_user_name="{current_user_name}"
        )
        logger.debug(f"[CRM Analysis Agent] Dynamic prompt loaded, length: {len(crm_analysis_agent_instructions)} characters")
        
        # Define callback to load context variables
        logger.info(f"[CRM Analysis Agent] Setting up context callback...")
        async def load_crm_analysis_context(callback_context):
            """Load context variables for the prompt template"""
            logger.debug(f"[CRM Analysis Agent] Loading context variables into callback_context...")
            callback_context.state["current_date"] = today_date
            callback_context.state["generation_type"] = generation_type
            callback_context.state["session_id"] = session_id
            logger.debug(f"[CRM Analysis Agent] Base context set: date={today_date}, type={generation_type}, session={session_id}")
            
            if full_name:
                callback_context.state["full_name"] = full_name
                logger.debug(f"[CRM Analysis Agent] Recipient name added: {full_name}")
            if current_user_name:
                callback_context.state["current_user_name"] = current_user_name
                logger.debug(f"[CRM Analysis Agent] Sender name added: {current_user_name}")
            
            logger.info(f"[CRM Analysis Agent] Context variables loaded successfully")
            return None
        
        logger.info(f"[CRM Analysis Agent] Context callback configured")
        
        # Get dynamic agent description using prompt factory
        logger.info(f"[CRM Analysis Agent] Loading dynamic agent description...")
        agent_description = prompt_factory.get_agent_description(agent_name, company_id)
        logger.debug(f"[CRM Analysis Agent] Agent description: {agent_description}")
        
        # Create agent without tools (simple generation agent)
        logger.info(f"[CRM Analysis Agent] Creating Kivo_LLMAgent instance...")
        logger.debug(f"[CRM Analysis Agent] Agent config: name='{agent_name}', output_key='crm_analysis_response'")
        
        crm_analysis_agent = Kivo_LLMAgent(
            name=agent_name,
            model=crm_analysis_model,
            instruction=crm_analysis_agent_instructions,
            description=agent_description,
            output_key="crm_analysis_response",
            tools=[],  # No tools needed for email generation
            before_agent_callback=load_crm_analysis_context,
            generate_content_config=balanced_generation_config
        )
        logger.info(f"[CRM Analysis Agent] Agent created successfully")
        logger.info(f"[CRM Analysis Agent] ========== AGENT INITIALIZATION COMPLETED ==========")
        
        return crm_analysis_agent
        
    except Exception as e:
        logger.error(f"Error in initiate_crm_analysis_agent: {e}", exc_info=True)
        raise

async def invoke_crm_analysis_agent(
    messages_text: str, 
    generation_type: str, 
    session_id: str, 
    company_id: int = None,
    origin: str = None,
    full_name: str = None,
    current_user_name: str = None
):
    """
    Invoke the CRM Analysis Agent to generate email content.
    
    Args:
        messages_text: Combined text messages from user
        generation_type: Type of email generation (reminder, greet, etc)
        session_id: Session identifier
        company_id: Company identifier (int)
        origin: Origin URL for LLM credentials
        full_name: Full name of the recipient for personalized emails
        current_user_name: Name of the current user sending the email
    
    Returns:
        dict: Generated email with subject and body
        str: Invocation ID
    """
    try:
        logger.info(f"[CRM Analysis Agent] ========== AGENT INVOCATION STARTED ==========")
        logger.info(f"[CRM Analysis Agent] Invocation params: generation_type={generation_type}")
        logger.info(f"[CRM Analysis Agent] Recipient: {full_name}, Sender: {current_user_name}")
        logger.debug(f"[CRM Analysis Agent] Session: {session_id}, Company: {company_id}")
        logger.debug(f"[CRM Analysis Agent] Messages text length: {len(messages_text)} characters")
        logger.debug(f"[CRM Analysis Agent] Messages preview: {messages_text[:200]}...")
        
        # Initialize the agent
        logger.info(f"[CRM Analysis Agent] Initializing agent...")
        agent = await initiate_crm_analysis_agent(
            session_id=session_id, 
            generation_type=generation_type,
            company_id=company_id,
            origin=origin,
            full_name=full_name,
            current_user_name=current_user_name
        )
        logger.info(f"[CRM Analysis Agent] Agent initialized successfully")
        
        # Prepare user input
        logger.info(f"[CRM Analysis Agent] Preparing LLM query input...")
        llm_query_json = {
            "messages": messages_text,
            "generation_type": generation_type
        }
        logger.debug(f"[CRM Analysis Agent] LLM query JSON: {json.dumps(llm_query_json, indent=2)[:300]}...")
        
        content = types.Content(
            role="user", 
            parts=[types.Part(text=json.dumps(llm_query_json, indent=2))]
        )
        logger.debug(f"[CRM Analysis Agent] Content object created with role=user")
        
        # Create DB session
        logger.info(f"[CRM Analysis Agent] Creating database session...")
        db_url = create_db_url()
        if not db_url:
            error_msg = "Invalid database URL"
            logger.error(f"[CRM Analysis Agent] ERROR: {error_msg}")
            raise ValueError(error_msg)
        logger.debug(f"[CRM Analysis Agent] Database URL created successfully")
        
        session_service = DatabaseSessionService(db_url=db_url)
        logger.debug(f"[CRM Analysis Agent] DatabaseSessionService initialized")
        
        agent_name = "crm_analysis_agent"
        
        logger.info(f"[CRM Analysis Agent] Retrieving or creating session...")
        session = await session_service.get_session(
            app_name=agent_name, 
            user_id=session_id, 
            session_id=session_id
        )
        if not session:
            logger.info(f"[CRM Analysis Agent] Session not found, creating new session...")
            session = await session_service.create_session(
                app_name=agent_name,
                user_id=session_id,
                session_id=session_id
            )
            logger.info(f"[CRM Analysis Agent] New session created successfully")
        else:
            logger.info(f"[CRM Analysis Agent] Existing session retrieved successfully")
        
        # Run the agent
        logger.info(f"[CRM Analysis Agent] ========== RUNNING AGENT ==========")
        logger.info(f"[CRM Analysis Agent] Creating Runner instance...")
        runner = Runner(agent=agent, app_name=agent_name, session_service=session_service)
        logger.info(f"[CRM Analysis Agent] Runner created, starting async execution...")
        
        response = None
        invocation_id = None
        event_count = 0
        
        logger.info(f"[CRM Analysis Agent] Streaming agent events...")
        async for event in runner.run_async(
            user_id=session_id, 
            session_id=session_id, 
            new_message=content
        ):
            event_count += 1
            invocation_id = event.invocation_id
            logger.debug(f"[CRM Analysis Agent] Event {event_count} received, invocation_id: {invocation_id}")
            
            if event.is_final_response():
                logger.info(f"[CRM Analysis Agent] Final response event received (event #{event_count})")
                if event.content is None or not hasattr(event.content, "parts") or not event.content.parts:
                    logger.warning(f"[CRM Analysis Agent] Event has no content, continuing to wait for valid response...")
                    continue
                else:
                    response = event.content.parts[0].text
                    logger.info(f"[CRM Analysis Agent] Response extracted successfully")
                    logger.debug(f"[CRM Analysis Agent] Response preview: {response[:200]}...")
                    logger.info(f"[CRM Analysis Agent] Response length: {len(response)} characters")
                    break
            else:
                logger.debug(f"[CRM Analysis Agent] Event {event_count}: Not final response, continuing...")
        
        logger.info(f"[CRM Analysis Agent] ========== AGENT EXECUTION COMPLETED ==========")
        logger.info(f"[CRM Analysis Agent] Total events processed: {event_count}")
        
        # Fallback if no response was set
        if response is None:
            error_msg = "No final response received from the agent"
            logger.error(f"[CRM Analysis Agent] ERROR: {error_msg}")
            logger.debug(f"[CRM Analysis Agent] Events received: {event_count}, Invocation ID: {invocation_id}")
            raise RuntimeError(error_msg)
        
        logger.info(f"[CRM Analysis Agent] Response received, parsing...")
        
        # Sanitize response - remove markdown code blocks if present
        sanitized_response = response.strip()
        logger.debug(f"[CRM Analysis Agent] Original response preview: {sanitized_response[:200]}...")
        
        # Remove ```json and ``` markers
        if sanitized_response.startswith("```json"):
            logger.debug(f"[CRM Analysis Agent] Removing ```json``` code block markers")
            sanitized_response = sanitized_response.replace("```json", "").replace("```", "").strip()
        elif sanitized_response.startswith("```"):
            logger.debug(f"[CRM Analysis Agent] Removing ``` code block markers")
            sanitized_response = sanitized_response.replace("```", "").strip()
        
        logger.debug(f"[CRM Analysis Agent] Sanitized response preview: {sanitized_response[:200]}...")
        
        # Parse response as JSON
        try:
            logger.debug(f"[CRM Analysis Agent] Attempting to parse response as JSON...")
            email_data = json.loads(sanitized_response)
            logger.info(f"[CRM Analysis Agent] JSON parsing successful")
            
            # Ensure the response has required fields
            if "email_subject" not in email_data or "email_body" not in email_data:
                logger.warning(f"[CRM Analysis Agent] Response missing required fields, wrapping in default format")
                logger.debug(f"[CRM Analysis Agent] Available keys: {list(email_data.keys())}")
                email_data = {
                    "email_subject": f"{generation_type.capitalize()} - Generated Email",
                    "email_body": sanitized_response
                }
                logger.info(f"[CRM Analysis Agent] Default format applied")
            else:
                logger.info(f"[CRM Analysis Agent] Required fields present: email_subject, email_body")
                logger.debug(f"[CRM Analysis Agent] Subject: {email_data['email_subject']}")
                
                # Check if email_body itself contains JSON (nested JSON issue)
                body = email_data['email_body']
                if body.strip().startswith('{') and body.strip().endswith('}'):
                    logger.debug(f"[CRM Analysis Agent] Detected potential nested JSON in email_body, attempting to parse...")
                    try:
                        nested_data = json.loads(body)
                        if "email_subject" in nested_data and "email_body" in nested_data:
                            logger.info(f"[CRM Analysis Agent] Found nested JSON structure, extracting actual email data")
                            email_data = nested_data
                            logger.debug(f"[CRM Analysis Agent] Extracted subject: {email_data['email_subject']}")
                    except json.JSONDecodeError:
                        logger.debug(f"[CRM Analysis Agent] email_body is not nested JSON, keeping as is")
                
                logger.debug(f"[CRM Analysis Agent] Final body length: {len(email_data['email_body'])} characters")
        except json.JSONDecodeError as json_error:
            logger.warning(f"[CRM Analysis Agent] Could not parse response as JSON: {json_error}")
            logger.debug(f"[CRM Analysis Agent] Raw response: {sanitized_response[:300]}...")
            email_data = {
                "email_subject": f"{generation_type.capitalize()} - Generated Email",
                "email_body": sanitized_response
            }
            logger.info(f"[CRM Analysis Agent] Formatted as plain text with default subject")
        
        logger.info(f"[CRM Analysis Agent] ========== INVOCATION COMPLETED SUCCESSFULLY ==========")
        logger.info(f"[CRM Analysis Agent] Invocation ID: {invocation_id}")
        logger.info(f"[CRM Analysis Agent] Returning email data with subject and body")
        
        return email_data, invocation_id
        
    except Exception as e:
        logger.error(f"Error in invoke_crm_analysis_agent: {e}", exc_info=True)
        raise

