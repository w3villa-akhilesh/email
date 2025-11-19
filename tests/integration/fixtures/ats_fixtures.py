import pytest
from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.agents.readonly_context import ReadonlyContext
from .ats_tool_mocks.get_job_applicants import MockGetJobApplicantsTool
from .ats_tool_mocks.get_job_profile_name import MockGetJobProfileNameTool
from .ats_tool_mocks.get_interview_detail_on_date import MockGetInterviewDetailOnDateTool
from .ats_tool_mocks.get_applicant_applied_on_date import MockGetApplicantAppliedOnDateTool
from .ats_tool_mocks.get_applicant_by_source_name import MockGetApplicantBySourceNameTool

class MockATSToolset(MCPToolset):
    """Mock implementation of MCPToolset for ATS tools."""

    def __init__(self):
        self._mcp_session_manager = MagicMock()
        self._errlog = MagicMock()
        self._tools = [
            MockGetJobApplicantsTool(),
            MockGetJobProfileNameTool(),
            MockGetInterviewDetailOnDateTool(),
            MockGetApplicantAppliedOnDateTool(),
            MockGetApplicantBySourceNameTool(),
        ]

    async def get_tools(self, context: ReadonlyContext = None):
        """Return mock tools."""
        return self._tools

    async def close(self):
        """Mock close method."""
        pass

@pytest.fixture
def mock_ats_toolset():
    """Fixture that provides a mock ATS toolset."""
    return MockATSToolset() 