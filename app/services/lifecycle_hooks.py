from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.base_tool import BaseTool
from typing import Optional, Dict, Any
from google.genai import types
from app.utils.logger import logger

async def save_data_in_triage_context(date:str, session_id: str, profile_block:str, callback_context: CallbackContext, preloaded_context)-> Optional[types.Content]:
    agent_name=callback_context.agent_name
    logger.info(f"Entering agent- {agent_name}")
    # Use setdefault to efficiently set state with defaults
    callback_context.state.setdefault("preloaded_context", preloaded_context)
    callback_context.state.setdefault("current_date", date)
    callback_context.state.setdefault("profile_info", profile_block)
    return None

async def save_data_in_crm_triage_context(date:str, session_id: str, profile_block:str, callback_context: CallbackContext)-> Optional[types.Content]:
    agent_name=callback_context.agent_name
    logger.info(f"Entering agent- {agent_name}")
    # Use setdefault to efficiently set state with defaults
    callback_context.state.setdefault("current_date", date)
    callback_context.state.setdefault("profile_info", profile_block)
    return None

async def save_data_in_user_context(date:str, session_id: str, profile_block:str, callback_context: CallbackContext, preloaded_context: str = None)-> Optional[types.Content]:
    agent_name=callback_context.agent_name
    logger.info(f"Entering agent- {agent_name}")
    # Use setdefault to efficiently set state with defaults
    callback_context.state.setdefault("current_date", date)
    callback_context.state.setdefault("profile_info", profile_block)
    callback_context.state.setdefault("preloaded_context", preloaded_context or "")
    return None

async def save_data_in_hrms_context(date:str, profile_block:str, callback_context: CallbackContext, preloaded_context:str = None, mode:str = None)-> Optional[types.Content]:
    agent_name=callback_context.agent_name
    logger.info(f"Entering agent: {agent_name}")
    # Use setdefault to efficiently set state with defaults
    callback_context.state.setdefault("mode", mode)
    callback_context.state.setdefault("preloaded_context", preloaded_context)
    callback_context.state.setdefault("current_date", date)
    callback_context.state.setdefault("profile_info", profile_block)
    return None


async def save_data_in_crm_context(date:str, profile_block:str, callback_context: CallbackContext, session_id:str)-> Optional[types.Content]:
    agent_name=callback_context.agent_name
    logger.info(f"Entering agent: {agent_name}")
    # Use setdefault to efficiently set state with defaults
    callback_context.state.setdefault("current_date", date)
    callback_context.state.setdefault("profile_info", profile_block)
    
    # Get session_id safely from the invocation context
    # session_id = getattr(callback_context._invocation_context.session, 'id', 'unknown') if hasattr(callback_context, '_invocation_context') and callback_context._invocation_context and callback_context._invocation_context.session else 'unknown'
    callback_context.state['session_id'] = session_id

    logger.debug(f"CRM context loaded - session_id: {callback_context.state['session_id']}, current_date: {callback_context.state['current_date']}")
    return None


def before_agent_invocation_callback_context(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Logs entry into agent and saves state before execution.
    """
    agent_name = callback_context.agent_name
    invocation_id = callback_context.invocation_id
    session_id = callback_context._invocation_context.session.id
    current_state = callback_context.state.to_dict()
    type = "agent"
    status = "before"

    logger.info(f"Entering agent: {agent_name}")
    
    # number_of_calls = get_agent_call_count(agent_name, session_id, type)+1

    # save_output_to_db(
    #     invocation_id=invocation_id,
    #     session_id=session_id,
    #     response=current_state,
    #     agent_name=agent_name,
    #     type=type,
    #     tool_name=None,
    #     number_of_calls=1,
    #     status=status
    # )
    return None


def after_agent_invocation_callback_context(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Logs agent completion and saves final state.
    """
    agent_name = callback_context.agent_name
    invocation_id = callback_context.invocation_id
    session_id = callback_context._invocation_context.session.id
    current_state = callback_context.state.to_dict()
    type = "agent"
    status = "after"
    logger.info(f"Exiting agent: {agent_name}")

    # logger.info(f"Exiting agent: {agent_name} with response: {str(current_state)}")
    # save_output_to_db(
    #     invocation_id=invocation_id,
    #     session_id=session_id,
    #     response=current_state,
    #     agent_name=agent_name,
    #     type=type,
    #     tool_name=None,
    #     number_of_calls=1,
    #     status=status
    # )
    return None


def simple_before_tool_modifier(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext
) -> Optional[Dict]:
    """
    Logs entry into tool execution.
    """
    agent_name = tool_context.agent_name
    tool_name = tool.name
    invocation_id = tool_context.invocation_id
    session_id = tool_context._invocation_context.session.id
    type = "tool"
    status = "before"

    logger.info(f"Tool Invoked: {tool_name} in agent: {agent_name} with args:{args}")
    # save_output_to_db(
    #     invocation_id=invocation_id,
    #     session_id=session_id,
    #     response=None,
    #     agent_name=agent_name,
    #     type=type,
    #     tool_name=tool_name,
    #     number_of_calls=1,
    #     status=status
    # )
    return None


def simple_after_tool_modifier(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext, tool_response: Dict
) -> Optional[Dict]:
    """
    Logs completion of tool execution.
    """
    agent_name = tool_context.agent_name
    tool_name = tool.name
    invocation_id = tool_context.invocation_id
    session_id = tool_context._invocation_context.session.id
    type = "tool"
    status = "after"

    # logger.info(f"Tool call completed: {tool_name} in agent: {agent_name} with args:{args} and response: {tool_response}")
    # save_output_to_db(
    #     invocation_id=invocation_id,
    #     session_id=session_id,
    #     response=tool_response,
    #     agent_name=agent_name,
    #     type=type,
    #     tool_name=tool_name,
    #     number_of_calls=1,
    #     status=status
    # )
    return None