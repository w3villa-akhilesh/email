from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_tool import MCPTool
from google.adk.tools.tool_context import ToolContext

class MockGetWorkFromHomeAndOfficeInfoTool(MCPTool):
    """Mock implementation of get_work_from_home_and_office_info tool."""
    
    def __init__(self):
        self._name = "get_work_from_home_and_office_info"
        self._description = """
    Tool to get day information of employees working from home/office.

    This assistant provides:
    - List of employee names working from the specified location (home/office)
    - Leave details if any

    How it works:
    - Searches active employee profiles
    - Filters by date and location
    - Returns detailed profile info

    If date is not provided, current date is used.
    Date format must be 'YYYY-MM-DD'. If incomplete, return an error.

    Args:
        session_id (str): session id to get information from redis server
        date (str): Date in format 'YYYY-MM-DD'
        location (str): "home" or "office" (default is "home")
        
    """
        self._mcp_tool = MagicMock()
        self._mcp_tool.inputSchema = {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "date": {"type": "string"},
                "location": {"type": "string"},
            },
            "required": ["session_id"],
        }
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    async def __call__(self, session_id: str, date: str = None, location: str = "home"):
        if location == "home":
            return {"employees": ["Rakesh Sharma", "Jane Doe"]}
        else:
            return {"employees": ["John Smith"]}

    async def run_async(self, *, args, tool_context: ToolContext):
        session_id = args.get("session_id") or tool_context._invocation_context.session.id
        date = args.get("date")
        location = args.get("location", "home")
        return await self.__call__(session_id=session_id, date=date, location=location) 