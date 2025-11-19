from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_tool import MCPTool
from google.adk.tools.tool_context import ToolContext

class MockGetAwardDetailTool(MCPTool):
    """Mock implementation of get_award_detail tool."""

    def __init__(self):
        self._name = "get_award_detail"
        self._description = "Tool to get Award information"
        self._mcp_tool = MagicMock()
        self._mcp_tool.inputSchema = {
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        }

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def __call__(self, session_id: str):
        return [{"award_name": "Innovator of the Year", "awarded_to": "Jane Doe"}]

    async def run_async(self, *, args, tool_context: ToolContext):
        session_id = args.get("session_id") or tool_context._invocation_context.session.id
        return await self.__call__(session_id=session_id) 