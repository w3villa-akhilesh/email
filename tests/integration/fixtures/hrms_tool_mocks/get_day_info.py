from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_tool import MCPTool
from google.adk.tools.tool_context import ToolContext

class MockGetDayInfoTool(MCPTool):
    """Mock implementation of get_day_info tool."""
    
    def __init__(self):
        self._name = "get_day_info"
        self._description = """
    Get a specific day's information or attendance for an employee by name and date from Kivo HRMS.
    If multiple employees share the same name, the response will return data for all matching users. 
    For example, searching for "John" may return details of multiple distinct employees named "John".
    This assistant provides the following employee details:
    - Working from 
    - Mood
    - Start time
    - End time
    - Total time
    - Leave includes: leave category (e.g. sick leave) and type (e.g. full day leave)
    
    Args:
        date (str): Date in 'YYYY-MM-DD' format.
        name (str): Employee full name.
        session_id (str): Session ID to get information from Redis server

    Returns:
        list of dict : Employee's day info or a message if not found.
    """
        self._mcp_tool = MagicMock()
        self._mcp_tool.inputSchema = {
            "type": "object",
            "properties": {
                "date": {"type": "string"},
                "name": {"type": "string"},
                "session_id": {"type": "string"},
            },
            "required": ["date", "name", "session_id"],
        }

    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    async def __call__(self, date: str, name: str, session_id: str):
        return [{"working_from": "office", "mood": "productive", "start_time": "09:00", "end_time": "18:00", "total_time": "9h"}]

    async def run_async(self, *, args, tool_context: ToolContext):
        date = args.get("date")
        name = args.get("name")
        session_id = args.get("session_id") or tool_context._invocation_context.session.id
        return await self.__call__(date=date, name=name, session_id=session_id) 