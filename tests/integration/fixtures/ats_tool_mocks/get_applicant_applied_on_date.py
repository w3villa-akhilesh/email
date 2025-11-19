from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_tool import MCPTool
from google.adk.tools.tool_context import ToolContext

class MockGetApplicantAppliedOnDateTool(MCPTool):
    """Mock implementation of get_applicant_applied_on_date tool."""
    
    def __init__(self):
        self._name = "get_applicant_applied_on_date"
        self._description = """
    Retrieve the number of applicants who applied on a specific date.

    Args:
        date (str): Target date in ISO format, 'YYYY-MM-DD'.
        session_id (str): session id to get information from redis server

    Returns:
        dict: returns  how many people submitted applications on the given date.
    """
        self._mcp_tool = MagicMock()
        self._mcp_tool.inputSchema = {
            "type": "object",
            "properties": {
                "date": {"type": "string"},
                "session_id": {"type": "string"},
            },
            "required": ["date", "session_id"],
        }
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    async def __call__(self, date: str, session_id: str):
        return {"applicant_count": 10}

    async def run_async(self, *, args, tool_context: ToolContext):
        date = args.get("date")
        session_id = args.get("session_id") or tool_context._invocation_context.session.id
        return await self.__call__(date=date, session_id=session_id) 