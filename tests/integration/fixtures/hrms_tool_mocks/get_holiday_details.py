from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_tool import MCPTool
from google.adk.tools.tool_context import ToolContext

class MockGetHolidayDetailsTool(MCPTool):
    """Mock implementation of get_holiday_details tool."""

    def __init__(self):
        self._name = "get_holiday_details"
        self._description = "Resolve arbitrary holiday queries."
        self._mcp_tool = MagicMock()
        self._mcp_tool.inputSchema = {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "title": {"type": "string"},
                "date": {"type": "string"},
                "branch_id": {"type": "integer"},
                "from_date": {"type": "string"},
                "to_date": {"type": "string"},
                "upcoming": {"type": "boolean"},
                "period": {"type": "string"},
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
        return {'holidays': [{'title': 'Independence Day', 'date': '2024-08-15'}]}

    async def run_async(self, *, args, tool_context: ToolContext):
        session_id = args.pop("session_id", None) or tool_context._invocation_context.session.id
        return await self.__call__(session_id=session_id, **args) 