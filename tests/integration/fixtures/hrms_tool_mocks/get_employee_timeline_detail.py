from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_tool import MCPTool
from google.adk.tools.tool_context import ToolContext

class MockGetEmployeeTimelineDetailTool(MCPTool):
    """Mock implementation of get_employee_timeline_detail tool."""
    
    def __init__(self):
        self._name = "get_employee_timeline_detail"
        self._description = "Fetch detailed work logs for a specific employee."
        self._mcp_tool = MagicMock()
        self._mcp_tool.inputSchema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "date": {"type": "string"},
                "session_id": {"type": "string"},
            },
            "required": ["name", "date", "session_id"],
        }

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def __call__(self, name: str, date: str, session_id: str):
        return [{"log": "Worked on API integration", "project": "Project Kivo"}]

    async def run_async(self, *, args, tool_context: ToolContext):
        name = args.get("name")
        date = args.get("date")
        session_id = args.get("session_id") or tool_context._invocation_context.session.id
        return await self.__call__(name=name, date=date, session_id=session_id) 