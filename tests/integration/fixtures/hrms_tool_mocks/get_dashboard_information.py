from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_tool import MCPTool
from google.adk.tools.tool_context import ToolContext

class MockGetDashboardInformationTool(MCPTool):
    """Mock implementation of get_dashboard_information tool."""
    
    def __init__(self):
        self._name = "get_dashboard_information"
        self._description = """
    Fetch the dashboard-related data including:
    - Total number of employees
    - Department counts
    - Project and branch counts
    - Attendance data (Work From Office, Work From Home, On Leave)

    Args:
        date (str): The date for which dashboard data is requested, in 'DD-MM-YYYY' format.
                    If no specific date is provided, use '00-00-0000'.
        session_id (str): session id to get information from redis server

    Returns:
        dict: A JSON-compatible dictionary containing HRMS dashboard-related data.
    """
        self._mcp_tool = MagicMock()
        self._mcp_tool.inputSchema = {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "date": {"type": "string"},
            },
            "required": ["session_id"],
        }
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    async def __call__(self, session_id: str, date: str = '00-00-0000'):
        """Return mock dashboard data."""
        return {
            "total_employees": 150,
            "department_counts": {"Engineering": 75, "HR": 10, "Sales": 25},
            "attendance_data": {"wfo": 100, "wfh": 40, "leave": 10},
        }

    async def run_async(self, *, args, tool_context: ToolContext):
        """Override the base method to directly return the mock response."""
        date = args.get("date", '00-00-0000')
        session_id = args.get("session_id") or tool_context._invocation_context.session.id
        return await self.__call__(session_id=session_id, date=date) 