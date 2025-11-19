import pytest
from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.agents.readonly_context import ReadonlyContext
from .story_tool_mocks.create_story_handler import MockCreateStoryHandlerTool

class MockStoryToolset(MCPToolset):
    """Mock implementation of MCPToolset for Story (PM Board) tools."""

    def __init__(self):
        self._mcp_session_manager = MagicMock()
        self._errlog = MagicMock()
        self._tools = [MockCreateStoryHandlerTool()]

    async def get_tools(self, context: ReadonlyContext = None):
        """Return mock tools."""
        return self._tools

    async def close(self):
        """Mock close method."""
        pass

@pytest.fixture
def mock_story_toolset():
    """Fixture that provides a mock Story toolset."""
    return MockStoryToolset() 