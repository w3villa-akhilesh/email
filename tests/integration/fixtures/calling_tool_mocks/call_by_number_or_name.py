from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_tool import MCPTool
from google.adk.tools.tool_context import ToolContext

class MockCallByNumberOrNameTool(MCPTool):
    """Mock implementation of call_by_number_or_name tool."""
    
    def __init__(self):
        self._name = "call_by_number_or_name"
        self._description = """
    Initiate a call to a given number or employee name using the Jio EVA API.
    If a name is provided, it first attempts to find the employee's phone number via HRMS.
    
    Args:
        callee_info (str): The phone number to call or the name of the employee.
        caller_number (str): The caller's phone number.
        session_id (str): The current session ID for HRMS authentication.
            
    Returns:
        dict: Response from the call masking API with call status or HRMS lookup status.
    """
        self._mcp_tool = MagicMock()
        self._mcp_tool.inputSchema = {
            "type": "object",
            "properties": {
                "callee_info": {"type": "string"},
                "caller_number": {"type": "string"},
                "session_id": {"type": "string"},
            },
            "required": ["callee_info", "caller_number", "session_id"],
        }
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    async def __call__(self, callee_info: str, caller_number: str, session_id: str):
        return {"status": f"call initiated to {callee_info} from {caller_number}"}

    async def run_async(self, *, args, tool_context: ToolContext):
        callee_info = args.get("callee_info")
        caller_number = args.get("caller_number")
        session_id = args.get("session_id") or tool_context._invocation_context.session.id
        return await self.__call__(callee_info=callee_info, caller_number=caller_number, session_id=session_id) 