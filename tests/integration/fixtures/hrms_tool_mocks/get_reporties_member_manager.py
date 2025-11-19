from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_tool import MCPTool
from google.adk.tools.tool_context import ToolContext

class MockGetReportiesMemberManagerTool(MCPTool):
    """Mock implementation of get_reporties_member_manager tool."""
    
    def __init__(self):
        self._name = "get_reporties_member_manager"
        self._description = "This tool provides reporties, members, manager information for a specific employee."
        self._mcp_tool = MagicMock()
        self._mcp_tool.inputSchema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "session_id": {"type": "string"},
                "type": {"type": "string", "enum": ["member","reporties","manager","reporting_manager","project_manager"]},
            },
            "required": ["name", "session_id", "type"],
        }
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    async def __call__(self, name: str, session_id: str, type: str):
        if type == "reporties":
            return {"reporties": ["Subordinate 1", "Subordinate 2"]}
        elif type == "manager":
            return {"manager": "Superior 1"}
        return {"message": "Invalid type specified."}

    async def run_async(self, *, args, tool_context: ToolContext):
        name = args.get("name")
        session_id = args.get("session_id") or tool_context._invocation_context.session.id
        type = args.get("type")
        return await self.__call__(name=name, session_id=session_id, type=type) 