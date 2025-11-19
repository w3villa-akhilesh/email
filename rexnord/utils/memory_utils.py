from google.adk.tools.tool_context import ToolContext
from app.utils.logger import logger

def memorize(key: str, value: str, tool_context: ToolContext):
    """
    Memorize pieces of information, one key-value pair at a time.

    Args:
        key: the label indexing the memory to store the value.
        value: the information to be stored.
        tool_context: The ADK tool context.

    Returns:
        A status message.
    """
    mem_dict = tool_context.state
    agent_name = tool_context.agent_name
    mem_dict[key] = value
    logger.debug(f"{agent_name} stored {key}: {value}")
    return {"status": f'Stored "{key}": "{value}"'} 