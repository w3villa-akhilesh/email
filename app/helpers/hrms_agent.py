from app.services.current_user_info import get_current_profile
from app.services.lifecycle_hooks import before_agent_invocation_callback_context, after_agent_invocation_callback_context, save_data_in_hrms_context, simple_after_tool_modifier, simple_before_tool_modifier
from app.services.mcp_connection import connect_to_mcp_server
from app.utils.logger import logger
from google.adk.agents.llm_agent import LlmAgent
from app.services.llm_engine import get_llm_engine
from datetime import datetime
from app.utils.prompt import MODE_RULES
from app.services.agent_prompt_service import agent_prompt_service
from app.core.constants import HRMS_MCP_SERVER_URL
from google.adk.agents.callback_context import CallbackContext
from app.models.schema import strict_generation_config
from app.sub_agents.triage.name_suggestion_agent import initiate_name_suggestion_agent
from app.sub_agents.hrms.hrms_questionnaire_workflow_agent import initiate_hrms_workflow_questionnaire_agent
from google.adk.tools.agent_tool import AgentTool
from fastapi import HTTPException
from app.services.agent_registry import AgentRegistryService
from app.services.email_notifier import send_exception_email
from app.helpers.BaseAgent import Kivo_LLMAgent
from app.utils.prompt import WHATSAPP_BUTTON_FORMATTER_PROMPT

async def safe_run_agent(agent_names, profile_block, session_id, user_email, app_name, company_id, origin, preloaded_context, mode):
    """Initialize multiple sub-agents safely with error handling"""
    safe_run_agents = []
    errors = []
    
    for agent_name in agent_names:
        try:
            # Prepare kwargs based on agent requirements
            kwargs = {
                "session_id": session_id,
                "company_id": company_id,
                "app_name": app_name,
                "origin": origin,
                "mode": mode
            }
            
            # Add common parameters that agents might need
            kwargs.update({
                "profile_block": profile_block,
                "preloaded_context": preloaded_context,
                "user_email": user_email
            })
            
            logger.info(f"Creating sub-agent instance for --> {agent_name} with parameters: {kwargs}")
            # Create agent instance dynamically
            agent_instance = await AgentRegistryService.create_agent_instance(agent_name, **kwargs)
            
            if agent_instance:
                safe_run_agents.append(agent_instance)
                logger.info(f"Successfully initialized sub-agent: {agent_name}")
            
        except Exception as e:
            logger.error(f"Error initializing {agent_name}: {str(e)}", exc_info=True)
            errors.append({"agent": agent_name, "error": str(e)})
            continue
        
    if errors:
        error_message = "\n".join(str(e) for e in errors)
        error_message = f"{error_message}\nSession ID: {session_id}\nOrigin: {origin}\nCompany ID: {company_id}"
        send_exception_email(
            Exception(error_message),
            f"Error initializing sub-agents in hrms_agent:\n{error_message}",
            session_id=session_id,
            origin=origin,
            company_id=company_id
        )

    return safe_run_agents

async def initiate_hrms_agent(session_id, profile_block, company_id, app_name, origin, preloaded_context, mode, user_email=None):
    try:
        logger.debug("initiate HRMS mcp tool connection ...")
        agent_type = ["hrms"]
        exclude_tool_type = ["leave", "ats"]
        include_tool_type = []
        hrms_toolset = await connect_to_mcp_server(HRMS_MCP_SERVER_URL, None, agent_type, exclude_tool_type, include_tool_type, session_id)
        if not hrms_toolset:
            logger.error("Failed to connect to MCP server or no tools available.")
            raise HTTPException(status_code=500, detail=f"Failed to connect to HRMS Agent MCP server")
        
        # Get child agents for hrms_agent by company ID
        sub_agents_to_attempt = AgentRegistryService.get_child_agent_names_for_company_by_id(company_id, "hrms_agent")
        logger.info(f"Using database-driven child agents for hrms_agent in company ID {company_id}: {sub_agents_to_attempt}")
        
        # Initialize sub-agents dynamically
        safe_run_agents = []
        if sub_agents_to_attempt:
            safe_run_agents = await safe_run_agent(
                sub_agents_to_attempt, 
                profile_block=profile_block, 
                session_id=session_id, 
                user_email=user_email,
                app_name=app_name, 
                company_id=company_id, 
                origin=origin, 
                preloaded_context=preloaded_context, 
                mode=mode
            )
        
        if safe_run_agents:
            for agent in safe_run_agents:
                logger.debug(f"Sub-agent initialized: {agent.name}")
        else:
            logger.warning("No sub-agents initialized for HRMS agent.")
        
        # name_suggestion_agent = await initiate_name_suggestion_agent(session_id, profile_block, company_id, app_name, origin)
        # name_suggestion_agent_tool = AgentTool(agent=name_suggestion_agent)
        name_suggestion_agent = await initiate_name_suggestion_agent(session_id, profile_block, company_id, app_name, origin, preloaded_context, mode)
        name_suggestion_agent_tool = AgentTool(agent=name_suggestion_agent)
        logger.debug(f"questionnaire_agent getting initialized with preloaded_context {preloaded_context}")
        questionnaire_agent = await initiate_hrms_workflow_questionnaire_agent(session_id, profile_block, company_id, app_name, origin, preloaded_context, mode)
        questionnaire_agent_tool = AgentTool(agent=questionnaire_agent) if questionnaire_agent else None
        
        logger.info("Setting up HRMS Agent")

        hrms_agent_model = get_llm_engine('hrms_agent', company_id)

        date= datetime.today().strftime("%Y-%m-%d %H:%M:%S %A")

        async def load_triage_context(callback_context: CallbackContext):
                            # Call the message checking function and use its return value
            return await save_data_in_hrms_context(date, profile_block, callback_context,preloaded_context,mode)

        # Combine HRMS operational tools with questionnaire workflow sub-agent
        all_tools = hrms_toolset + ([questionnaire_agent_tool] if questionnaire_agent_tool else []) + ([name_suggestion_agent_tool] if name_suggestion_agent_tool else [])
        # Get dynamic prompt based on company's available agents
        dynamic_prompt = agent_prompt_service.get_agent_prompt(
            agent_name="hrms_agent",
            company_id=company_id,
            session_id=session_id,
            profile_info=profile_block,
            preloaded_context=preloaded_context,
            mode=mode
        )
        
        # Combine dynamic prompt with shared mode rules
        combined_instruction = f"{dynamic_prompt}\n\n{MODE_RULES}\n\n{WHATSAPP_BUTTON_FORMATTER_PROMPT}"

        kivo_hrms_agent = Kivo_LLMAgent(
            name="hrms_agent",
            model=hrms_agent_model,
            instruction=combined_instruction,
            description=agent_prompt_service.get_agent_description("hrms_agent", company_id),
            output_key="final_summary",
            tools=all_tools,
            sub_agents=safe_run_agents,
            before_agent_callback=load_triage_context, # check before executing agent
            after_agent_callback=after_agent_invocation_callback_context,    # check after executing agent
            before_tool_callback=simple_before_tool_modifier,
            after_tool_callback=simple_after_tool_modifier # Assign the callback
            # generate_content_config=strict_generation_config

        )
        return kivo_hrms_agent  # Return the agent here
    except Exception as e:
        logger.error(f"Error in initiate_hrms_agent: {e}", exc_info=True)
        raise HTTPException( status_code=500, detail=f"hrms_agent initialization failed: {str(e)}" )
    finally:
       if hrms_toolset:
            try:
                await hrms_toolset.close()
            except Exception as e:
                logger.warning(f"Toolset close error: {e}", exc_info=True)