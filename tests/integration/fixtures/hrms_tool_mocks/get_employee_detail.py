from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_tool import MCPTool
from google.adk.tools.tool_context import ToolContext

class MockGetEmployeeDetailTool(MCPTool):
    """Mock implementation of get_employee_detail tool."""
    
    def __init__(self):
        self._name = "get_employee_detail"
        self._description = """
    Tool to get detailed information of a specific employee.
    This tool handles query like who is <employee_name> or details of <employee_name>.

    This assistant provides the following employee details:
    - Full Name
    - Email
    - Current Work Log 
    - Date of Birth (DOB)
    - Designation
    - Employee Code
    - Phone number
    - Profile link

    Args:
        name (str): name of the employee
        session_id (str): session id to get information from redis server

    Returns:
        A dictionary containing the employee's details.

    If name is not provided, returns a prompt asking for the name.
    """
        # This is needed because the base class's _get_declaration method uses it.
        self._mcp_tool = MagicMock()
        self._mcp_tool.inputSchema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "session_id": {"type": "string"},
            },
            "required": ["name", "session_id"],
        }
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    async def __call__(self, name: str, session_id: str):
        """Return mock response based on employee name."""
        if "rakesh" in name.lower() and "sharma" in name.lower():
            return {
                "employee_name": "Rakesh Sharma",
                "email": "rakesh.sharma@example.com",
                "current_work_log": "Working on mock implementation.",
                "dob": "1990-01-01",
                "designation": "Senior Software Engineer",
                "employee_code": "E12345",
                "phone_number": "123-456-7890",
                "profile link": "http://example.com/profiles/123",
            }
        elif "jane" in name.lower() and "doe" in name.lower():
            return {
                "employee_name": "Jane Doe",
                "email": "jane.doe@kivo.ai",
                "employee_code": "1234567890",
            }
        elif name.lower() == "ishan":
             return "multiple user found for the [{'employee_name': 'Ishank Gupta'}, {'employee_name': 'Ishan Chauhan'}]"
        elif name == "not_found":
            return f"No user found for {name}"
        else:
            return {"error": "An unexpected error occurred while fetching employee details."}

    async def run_async(self, *, args, tool_context: ToolContext):
        """Override the base method to directly return the mock response."""
        name = args.get("name")
        # The agent framework might pass session_id via tool_context
        session_id = args.get("session_id") or tool_context._invocation_context.session.id
        return await self.__call__(name=name, session_id=session_id) 