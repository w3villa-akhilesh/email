from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_tool import MCPTool
from google.adk.tools.tool_context import ToolContext

class MockGetTodayDateTool(MCPTool):
    """Mock implementation of get_today_date tool."""
    
    def __init__(self):
        self._name = "get_today_date"
        self._description = """
    Returns the current date in YYYY-MM-DD format.
    
    This function retrieves the today's or current system date returns it as a string.

    Returns:
        str: The current date in 'YYYY-MM-DD' format.
    """
        self._mcp_tool = MagicMock()
        self._mcp_tool.inputSchema = {"type": "object", "properties": {}}

    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    async def __call__(self):
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d')

    async def run_async(self, *, args, tool_context: ToolContext):
        return await self.__call__() 