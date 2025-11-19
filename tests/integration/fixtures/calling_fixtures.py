import pytest
from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.agents.readonly_context import ReadonlyContext
from .calling_tool_mocks.call_by_number_or_name import MockCallByNumberOrNameTool

class MockCallingToolset(MCPToolset):
    """Mock implementation of MCPToolset for Calling tools."""

    def __init__(self):
        self._mcp_session_manager = MagicMock()
        self._errlog = MagicMock()
        self._tools = [MockCallByNumberOrNameTool()]

    async def get_tools(self, context: ReadonlyContext = None):
        """Return mock tools."""
        return self._tools

    async def close(self):
        """Mock close method."""
        pass

@pytest.fixture
def mock_calling_toolset():
    """Fixture that provides a mock Calling toolset."""
    return MockCallingToolset() 