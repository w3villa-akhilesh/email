from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_tool import MCPTool
from google.adk.tools.tool_context import ToolContext

class MockGetJobProfileNameTool(MCPTool):
    """Mock implementation of get_job_profile_name tool."""
    
    def __init__(self):
        self._name = "get_job_profile_name"
        self._description = """
    this tool provides information about job details based on the job title.
    It provides information like job title, job profile, job description, location, number of openings/postions, rounds of interview, 
    maximum/minimum experience, targeted date

    Args:
        title (str): Title to filter job profiles by.
        session_id (str): session id to get information from redis server

    Returns:
        dict: Dictionary containing the job profile name.
    """
        self._mcp_tool = MagicMock()
        self._mcp_tool.inputSchema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "session_id": {"type": "string"},
            },
            "required": ["title", "session_id"],
        }
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    async def __call__(self, title: str, session_id: str):
        return {"job_title": title, "profile": "Software Engineer Profile"}

    async def run_async(self, *, args, tool_context: ToolContext):
        title = args.get("title")
        session_id = args.get("session_id") or tool_context._invocation_context.session.id
        return await self.__call__(title=title, session_id=session_id) 