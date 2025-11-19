import pytest
from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.agents.readonly_context import ReadonlyContext
from .hrms_tool_mocks.get_award_detail import MockGetAwardDetailTool
from .hrms_tool_mocks.get_dashboard_information import MockGetDashboardInformationTool
from .hrms_tool_mocks.get_day_info import MockGetDayInfoTool
from .hrms_tool_mocks.get_emp_on_leave import MockGetEmpOnLeaveTool
from .hrms_tool_mocks.get_employee_detail import MockGetEmployeeDetailTool
from .hrms_tool_mocks.get_employee_leave_detail import MockGetEmployeeLeaveDetailTool
from .hrms_tool_mocks.get_employee_projects import MockGetEmployeeProjectsTool
from .hrms_tool_mocks.get_employee_timeline_detail import MockGetEmployeeTimelineDetailTool
from .hrms_tool_mocks.get_event_details import MockGetEventDetailsTool
from .hrms_tool_mocks.get_holiday_details import MockGetHolidayDetailsTool
from .hrms_tool_mocks.get_leave_detail import MockGetLeaveDetailTool
from .hrms_tool_mocks.get_offered_candidate_detail import MockGetOfferedCandidateDetailTool
from .hrms_tool_mocks.get_reporties_member_manager import MockGetReportiesMemberManagerTool
from .hrms_tool_mocks.get_today_date import MockGetTodayDateTool
from .hrms_tool_mocks.get_work_from_home_and_office_info import MockGetWorkFromHomeAndOfficeInfoTool
from .hrms_tool_mocks.leave_and_day_info import MockLeaveAndDayInfoTool

class MockHRMSToolset(MCPToolset):
    """Mock implementation of MCPToolset for HRMS tools."""
    
    def __init__(self):
        self._mcp_session_manager = MagicMock()
        self._errlog = MagicMock()
        self._tools = [
            MockGetEmployeeDetailTool(),
            MockGetDashboardInformationTool(),
            MockGetEmployeeLeaveDetailTool(),
            MockGetEmployeeProjectsTool(),
            MockLeaveAndDayInfoTool(),
            MockGetDayInfoTool(),
            MockGetTodayDateTool(),
            MockGetWorkFromHomeAndOfficeInfoTool(),
            MockGetEmpOnLeaveTool(),
            MockGetHolidayDetailsTool(),
            MockGetEventDetailsTool(),
            MockGetAwardDetailTool(),
            MockGetOfferedCandidateDetailTool(),
            MockGetLeaveDetailTool(),
            MockGetEmployeeTimelineDetailTool(),
            MockGetReportiesMemberManagerTool(),
        ]
    
    async def get_tools(self, context: ReadonlyContext = None):
        """Return mock tools."""
        return self._tools
    
    async def close(self):
        """Mock close method."""
        pass

@pytest.fixture
def mock_hrms_toolset():
    """Fixture that provides a mock HRMS toolset."""
    return MockHRMSToolset() 