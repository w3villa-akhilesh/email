import json
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.llm_agent import LlmAgent
from google.genai import types
from google.adk.sessions import DatabaseSessionService
from google.adk.runners import Runner
from app.services.lifecycle_hooks import after_agent_invocation_callback_context, before_agent_invocation_callback_context, simple_after_tool_modifier, simple_before_tool_modifier
from app.services.llm_engine import get_llm_engine
from app.services.mcp_connection import connect_to_mcp_server
from app.utils.prompt import KIVO_AGENT_PROMPT
from app.utils.logger import logger
from app.core.constants import PM_BOARD_AGENT_NAME
from app.services.email_notifier import send_exception_email
from app.services.my_sql_client import create_db_url
from app.core.constants import SLACK_MCP_SERVER_URL
from google.adk.models.lite_llm import LiteLlm
import os
from dotenv import load_dotenv
from app.services.redis_common_state import get_session_data
load_dotenv()

async def initiate_pm_board_agent(project_instructions:str, data: dict, ka_session_id: str, ka_user_id: str, company_id: str, app_name: str, origin: str):
    try:
        logger.debug(project_instructions)
        
        # Resolve model via company-specific credentials similar to HRMS
        pm_board_agent_model = get_llm_engine('Kivo_PM_Board_Agent', company_id, app_name, origin)

        # connecting with mcp server
        pm_board_validation_toolset = await connect_to_mcp_server(server_url=SLACK_MCP_SERVER_URL)

        logger.info("Setting up Kivo Agent")

        def pm_board_before_tool_modifier(tool, args, tool_context):
            updated_args = dict(args) if args else {}

            if tool.name in {"send_slack_message_by_user_id", "send_slack_message_by_role", "send_cc_to_admin"}:
                project_id = updated_args.get("project_id") or tool_context.state.get("project_id")
                if project_id:
                    updated_args["project_id"] = project_id
                else:
                    logger.warning(
                        f"project_id missing for {tool.name} in session {tool_context._invocation_context.session.id}; tool may fail validation."
                    )

            simple_before_tool_modifier(tool, updated_args, tool_context)

            return updated_args if updated_args != args else None

        pm_board_agent = LlmAgent(
            name=PM_BOARD_AGENT_NAME,
            model=pm_board_agent_model,
            instruction=f"{KIVO_AGENT_PROMPT}",
            description="Perform tool call with provided data in `processed_input`.",
            output_key="final_summary",
            tools=pm_board_validation_toolset,
            before_agent_callback=before_agent_invocation_callback_context, # check before executing agent
            after_agent_callback=after_agent_invocation_callback_context,    # check after executing agent
            before_tool_callback=pm_board_before_tool_modifier,
            after_tool_callback=simple_after_tool_modifier # Assign the callback
        )

        # Create or verify the database URL
        verified_db_url=create_db_url()
        if not verified_db_url:
            logger.error("Database URL is not configured properly.")
            return None
        
        # Building SequentialAgent for orchestrating pm_board_agent
        Kivo_Agent = SequentialAgent(name="story_validation_main_agent", sub_agents=[pm_board_agent])
        session_service = DatabaseSessionService(db_url=verified_db_url)
        context_session_data= await session_service.create_session(app_name="story_validation_agent", user_id=ka_user_id, session_id=ka_session_id)

        # Load project context (if any) saved against this session
        session_cache = get_session_data(ka_session_id)
        project_id = session_cache.get("project_id") if session_cache else None
        if project_id:
            # Expose project_id to the agent state so tools can reference it
            context_session_data.state['project_id'] = project_id
        
        #runner initialized
        logger.info("Kivo Agent and Runner initialized.")
        runner = Runner(agent=Kivo_Agent, app_name="story_validation_agent", session_service=session_service,)

        # Include project_id in the query to help the LLM provide required tool args
        if project_id:
            query = f"process data: {data} with project_id: {project_id} and follow below steps in sequence {project_instructions}."
        else:
            query = f"process data: {data} and follow below steps in sequence {project_instructions}."
        content = types.Content(role='user', parts=[types.Part(text=query)])

        context_session_data.state['agent_purpose']="Analyze pm board data and perform tool call."
        logger.debug(f"session data: {context_session_data.state}")
        
        # logging all agents and tool calls
        async for event in runner.run_async(user_id=ka_user_id, session_id=ka_session_id, new_message=content):
            author = event.author or "Kivo Agent"

            if event.is_final_response():
                if event.content.parts:                                   # length check
                    final_response = event.content.parts[0].text
                else:
                    final_response = "(no text part)"
                logger.debug(f"[{ka_session_id}] Response from {author}:\n{final_response}")

                continue                    

            for part in event.content.parts:
                if part.function_call:
                    fn = part.function_call
                    if fn and fn.args:
                        logger.debug(f"[{ka_session_id}] Tool Call by {author}:\n- Tool\n- Args:\n{json.dumps(fn.args, indent=2)}")
                elif part.function_response:
                    fr = part.function_response
                    result = fr.response["result"]
                    output = result.content[0].text if result.content else "(no output)"
                    status = "Error" if result.isError else "Success"
                    logger.info(f"[{ka_session_id}] Tool Response to {author}:\n{status}:\n{output}")
                    

        return {
            "user_id": ka_user_id,
            "session_id": ka_session_id,
        }

    except Exception as e:
        logger.error(f"Error in initiate_kivo_agent: {e}")
        send_exception_email(f"Error in initiate_kivo_agent: {str(e)}", e)
        return None
    
    finally:
        pass
