from unittest.mock import MagicMock
from google.adk.tools.mcp_tool.mcp_tool import MCPTool
from google.adk.tools.tool_context import ToolContext

class MockCreateStoryHandlerTool(MCPTool):
    """Mock implementation of create_story_handler tool."""

    def __init__(self):
        self._name = "create_story_handler"
        self._description = """
    Create a story/task after validating project name and assignee name, then confirming user intent.
    1-Args:
    - session_id (str): Unique context ID.
    - user_name (str): Story assignee.
    - title (str): Always create suitable title based on story information, start with an action verb, mention system/module, avoid project name, use sentence case, keep it 6–10 words.
    - description (str): Always create description based on story information, should not contain project name, keep it informative and upto 1 line.
    - project_name (str): Required for validation.
    - status_keyword (str): Story status(To-do,In Progress,Finished,Archived), default = "To-do".
    - confirmation_intent (str): Default is "No". Use intent to decide: "Yes" to proceed, otherwise show preview.
    - deadline (str): Optional natural language deadline,Do not assume deadline unless specified, Accepts natural language ("2 hours", "1 day").
    - selected_sprint_name (str, optional): Name of sprint chosen by user, if any.
    2-Modifications:
    - If user wants to change title, description, project, assignee, or deadline, show preview and ask for confirmation.
    3-Returns:
    - If invalid project/assignee: error with hint.
    - If not confirmed: story preview for confirmation.
    - If confirmed: creates story and return {Title": story_title, "Link": story_link}.
    Note:
    - Story is only created **after** successful validation and **explicit positive confirmation**.
    """
        self._mcp_tool = MagicMock()
        self._mcp_tool.inputSchema = {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "user_name": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "project_name": {"type": "string"},
                "status_keyword": {"type": "string"},
                "confirmation_intent": {"type": "string"},
                "deadline": {"type": "string"},
                "selected_sprint_name": {"type": "string"},
            },
            "required": ["session_id", "user_name", "title", "description", "project_name"],
        }

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def __call__(self, **kwargs):
        if kwargs.get("confirmation_intent") == "Yes":
            return {"Title": kwargs.get("title"), "Link": "http://example.com/story/123"}
        else:
            return f"Preview of story to be created: {kwargs}"

    async def run_async(self, *, args, tool_context: ToolContext):
        args["session_id"] = args.get("session_id") or tool_context._invocation_context.session.id
        return await self.__call__(**args) 