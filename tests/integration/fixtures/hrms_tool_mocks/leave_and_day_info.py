from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_tool import MCPTool
from google.adk.tools.tool_context import ToolContext

class MockLeaveAndDayInfoTool(MCPTool):
    """Mock implementation of leave_and_day_info tool."""
    
    def __init__(self):
        self._name = "leave_and_day_info"
        self._description = """
    Extracts leave and day information from the provided data.

    Args:
        data (dict): The data containing leave and day information.

    Returns:
        dict: A dictionary containing leave and day information.
    """
        self._mcp_tool = MagicMock()
        self._mcp_tool.inputSchema = {
            "type": "object",
            "properties": {
                "data": {"type": "object"},
            },
            "required": ["data"],
        }

    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    async def __call__(self, data: dict):
        return {"leave_info": "extracted_leave_info", "day_info": "extracted_day_info"}

    async def run_async(self, *, args, tool_context: ToolContext):
        data = args.get("data")
        return await self.__call__(data=data) 