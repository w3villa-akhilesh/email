from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_tool import MCPTool
from google.adk.tools.tool_context import ToolContext

class MockGetApplicantBySourceNameTool(MCPTool):
    """Mock implementation of get_applicant_by_source_name tool."""
    
    def __init__(self):
        self._name = "get_applicant_by_source_name"
        self._description = """
    Get how many applicants came from a particular source.

    This function looks up your applicant tracking system and counts
    how many people applied via the given source name (for example,
    "LinkedIn" or "Employee Referral"), using your session token
    (pulled from Redis via session_id) to authenticate.

    Args:
        name (str): The name of the sourcing channel.
        session_id (str): Session ID to retrieve auth token from Redis.


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
        return {"source_name": name, "applicant_count": 5}

    async def run_async(self, *, args, tool_context: ToolContext):
        name = args.get("name")
        session_id = args.get("session_id") or tool_context._invocation_context.session.id
        return await self.__call__(name=name, session_id=session_id) 