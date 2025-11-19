from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_tool import MCPTool
from google.adk.tools.tool_context import ToolContext

class MockGetOfferedCandidateDetailTool(MCPTool):
    """Mock implementation of get_offered_candidate_detail tool."""

    def __init__(self):
        self._name = "get_offered_candidate_detail"
        self._description = "Fetch offered candidate profiles."
        self._mcp_tool = MagicMock()
        self._mcp_tool.inputSchema = {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "name": {"type": "string"},
            },
            "required": ["session_id"],
        }

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def __call__(self, session_id: str, name: str = None):
        candidates = [{"full_name": "Prospective Hire 1", "status": "offered"}, {"full_name": "Prospective Hire 2", "status": "offered"}]
        if name:
            return next((c for c in candidates if name.lower() in c['full_name'].lower()), {"message": "Candidate not found"})
        return candidates

    async def run_async(self, *, args, tool_context: ToolContext):
        session_id = args.get("session_id") or tool_context._invocation_context.session.id
        name = args.get("name")
        return await self.__call__(session_id=session_id, name=name) 