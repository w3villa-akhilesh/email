from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_tool import MCPTool
from google.adk.tools.tool_context import ToolContext

class MockGetEmployeeProjectsTool(MCPTool):
    """Mock implementation of get_employee_projects tool."""
    
    def __init__(self):
        self._name = "get_employee_projects"
        self._description = """
    Tool to get information of project (assignment) for a specific employee.

    Args:
        name (str): Employee's name
        session_id (str): session id to get information from redis server
    Returns:
        dict: Contains employee info and assigned projects or error message
        
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
        return {"employee_name": name, "projects": ["Project Kivo", "Project Agent"]}

    async def run_async(self, *, args, tool_context: ToolContext):
        name = args.get("name")
        session_id = args.get("session_id") or tool_context._invocation_context.session.id
        return await self.__call__(name=name, session_id=session_id) 