from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_tool import MCPTool
from google.adk.tools.tool_context import ToolContext

class MockGetJobProfileTool(MCPTool):
    """Mock implementation of get_job_profile tool."""

    def __init__(self):
        self._name = "get_job_profile"
        self._description = "Tool to get Job Profile information"
        self._mcp_tool = MagicMock()
        self._mcp_tool.inputSchema = {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "job_title": {"type": "string"}
            },
            "required": ["session_id", "job_title"],
        }

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def __call__(self, session_id: str, job_title: str):
        result = []
        if job_title == "Software Engineer":
            job_profile = {
                "job_profile": "Software Engineer",
                "job_description": "Software Engineer",
                "job_location": "New York",
                "job_salary": "100000",
                "job_experience": "5 years",
                "job_skills": "Python, Java, SQL",
                "job_education": "Bachelor's Degree",
                "job_type": "Full-time",
                "job_status": "Active"
            }
            result.append(job_profile)
        
        return result

    async def run_async(self, *, args, tool_context: ToolContext):
        session_id = args.get("session_id") or tool_context._invocation_context.session.id
        job_title = args.get("job_title")
        return await self.__call__(session_id=session_id, job_title=job_title) 