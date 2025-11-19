from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_tool import MCPTool
from google.adk.tools.tool_context import ToolContext

class MockGetEmployeeLeaveDetailTool(MCPTool):
    """Mock implementation of get_employee_leave_detail tool."""
    
    def __init__(self):
        self._name = "get_employee_leave_detail"
        self._description = """
    this tool provide the information of leave detail like sick leave, privillege leave and casual leave of employee

    Args:
        name(str):name of the employee
        session_id (str): session id to get information from redis server
        
    Returns:
        return the information of the employee like total leave detail, sick leave and casual leave
    """
        self._mcp_tool = MagicMock()
        self._mcp_tool.inputSchema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "session_id": {"type": "string"},
            },
            "required": ["name", "session_id"],
        }
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    async def __call__(self, name: str, session_id: str):
        return {"sick_leave": 5, "privilege_leave": 10, "casual_leave": 5}

    async def run_async(self, *, args, tool_context: ToolContext):
        name = args.get("name")
        session_id = args.get("session_id") or tool_context._invocation_context.session.id
        return await self.__call__(name=name, session_id=session_id) 