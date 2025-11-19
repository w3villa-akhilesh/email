from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_tool import MCPTool
from google.adk.tools.tool_context import ToolContext

class MockGetEmpOnLeaveTool(MCPTool):
    """Mock implementation of get_emp_on_leave tool."""
    
    def __init__(self):
        self._name = "get_emp_on_leave"
        self._description = """
    Tool to get day information of employees on leave for given date.

    This assistant provides:
    - List of employee names who are on leave
    - Leave details if any

    How it works:
    - Searches active employee profiles
    - Filters by date 
    - Returns detailed profile info

    If date is not provided, current date is used.
    Date format must be 'YYYY-MM-DD'. If incomplete, return an error.

    Args:
        session_id (str): session id to get information from redis server
        date (str): Date in format 'YYYY-MM-DD'
        
        
    """
        self._mcp_tool = MagicMock()
        self._mcp_tool.inputSchema = {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "date": {"type": "string"},
            },
            "required": ["session_id"],
        }
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    async def __call__(self, session_id: str, date: str = None):
        return {"employees_on_leave": ["Peter Jones", "Mary Jane"]}

    async def run_async(self, *, args, tool_context: ToolContext):
        session_id = args.get("session_id") or tool_context._invocation_context.session.id
        date = args.get("date")
        return await self.__call__(session_id=session_id, date=date) 