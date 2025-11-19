from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_tool import MCPTool
from google.adk.tools.tool_context import ToolContext

class MockGetJobApplicantsTool(MCPTool):
    """Mock implementation of get_job_applicants tool."""
    
    def __init__(self):
        self._name = "get_job_applicants"
        self._description = """
    Fetches job applicants based on the provided date.

    Args:
        name (str): Name to filter applicants by (used only when type is 'name').
        session_id (str): session id to get information from redis server


    Returns:
        Union[str, list]: Count string or list of applicants.
    """
        self._mcp_tool = MagicMock()
        self._mcp_tool.inputSchema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "session_id": {"type": "string"},
            },
            "required": ["session_id"],
        }
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    async def __call__(self, name: str, session_id: str):
        return ["applicant1", "applicant2"]

    async def run_async(self, *, args, tool_context: ToolContext):
        name = args.get("name")
        session_id = args.get("session_id") or tool_context._invocation_context.session.id
        return await self.__call__(name=name, session_id=session_id) 