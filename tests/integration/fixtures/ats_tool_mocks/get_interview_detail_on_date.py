from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_tool import MCPTool
from google.adk.tools.tool_context import ToolContext

class MockGetInterviewDetailOnDateTool(MCPTool):
    """Mock implementation of get_interview_detail_on_date tool."""
    
    def __init__(self):
        self._name = "get_interview_detail_on_date"
        self._description = """
    this tool provides information about interview schedule on given date.

    Args:
        date (str): date to find information regrading to the interview schedule information. 
                    date formate is 'YYYY-MM-DD'
        session_id (str): session id to get information from redis server

    Returns:
        dict: Dictionary containing the job profile name.
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
        return {"interviews": [{"candidate": "John Doe", "time": "10:00 AM"}]}

    async def run_async(self, *, args, tool_context: ToolContext):
        date = args.get("date")
        session_id = args.get("session_id") or tool_context._invocation_context.session.id
        return await self.__call__(date=date, session_id=session_id) 