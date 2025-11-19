from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_tool import MCPTool
from google.adk.tools.tool_context import ToolContext

class MockGetLeaveDetailTool(MCPTool):
    """Mock implementation of get_leave_detail tool."""

    def __init__(self):
        self._name = "get_leave_detail"
        self._description = "This tool returns leave entries for an employee."
        self._mcp_tool = MagicMock()
        self._mcp_tool.inputSchema = {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "full_name": {"type": "string"},
                "from_date": {"type": "string"},
                "to_date": {"type": "string"},
                "status": {"type": "string"},
            },
            "required": ["session_id"],
        }

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def __call__(self, session_id: str, **kwargs):
        return {"leaves": [{"employee": "Rakesh Sharma", "from": "2024-08-01", "to": "2024-08-02", "status": "approved"}], "count": 1}

    async def run_async(self, *, args, tool_context: ToolContext):
        session_id = args.pop("session_id", None) or tool_context._invocation_context.session.id
        return await self.__call__(session_id=session_id, **args) 