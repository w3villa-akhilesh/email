import pytest
import warnings
from unittest.mock import MagicMock
from tests.integration.fixtures.mcp_fixtures import mock_mcp_connections, mock_mcp_auth

# Suppress the specific RuntimeWarning from litellm
warnings.filterwarnings("ignore", message="coroutine 'Logging.async_success_handler' was never awaited")

from app.services import mcp_connection, mcp_auth
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.sessions import Session, InMemorySessionService
from google.adk.tools.tool_context import ToolContext
from tests.utils.llm_assert import assert_intents_present

@pytest.fixture
def mock_invocation_context():
    """Create a mock invocation context for testing."""
    mock_agent = MagicMock(spec=LlmAgent)
    mock_session_service = MagicMock(spec=InMemorySessionService)
    mock_session = MagicMock(spec=Session)
    mock_session.id = "test_session"  # Provide an id for the tool
    
    return InvocationContext(
        session_service=mock_session_service,
        invocation_id="mock_id",
        agent=mock_agent,
        session=mock_session,
    )

@pytest.mark.asyncio
async def test_hrms_agent_with_employee_detail_mock(mock_mcp_connections, mock_mcp_auth):
    """Test HRMS agent with mocked employee detail tool."""
    from app.helpers.hrms_agent import initiate_hrms_agent
    
    hrms_agent = await initiate_hrms_agent()
    assert isinstance(hrms_agent, LlmAgent)
    
    # Test agent with a mock query
    from google.genai import types
    from google.adk.runners import Runner
    
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="hrms_agent",
        user_id="test_user",
        session_id="test_session_employee"
    )
    
    runner = Runner(
        agent=hrms_agent,
        app_name="hrms_agent",
        session_service=session_service
    )
    
    content = types.Content(role='user', parts=[types.Part(text="give me details of Rakesh Sharma")])
    
    final_response_text = ""
    async for event in runner.run_async(
        user_id="test_user",
        session_id="test_session_employee",
        new_message=content
    ):
        if event.is_final_response():
            assert event.content is not None
            assert len(event.content.parts) > 0
            final_response_text = event.content.parts[0].text

    # Check that the agent's response contains the key details.
    intents_to_check = [
        "Rakesh Sharma",
        "Senior Software Engineer",
        "employee_code is E12345"
    ]
    assert await assert_intents_present(final_response_text, intents_to_check)


@pytest.mark.asyncio
async def test_hrms_agent_with_employee_detail_mock_multiple_users(mock_mcp_connections, mock_mcp_auth):
    """Test HRMS agent with mocked employee detail tool."""
    from app.helpers.hrms_agent import initiate_hrms_agent
    
    hrms_agent = await initiate_hrms_agent()
    assert isinstance(hrms_agent, LlmAgent)
    
    # Test agent with a mock query
    from google.genai import types
    from google.adk.runners import Runner
    
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="hrms_agent",
        user_id="test_user",
        session_id="test_session_employee"
    )
    
    runner = Runner(
        agent=hrms_agent,
        app_name="hrms_agent",
        session_service=session_service
    )
    
    content = types.Content(role='user', parts=[types.Part(text="give me details of Ishan")])
    
    final_response_text = ""
    async for event in runner.run_async(
        user_id="test_user",
        session_id="test_session_employee",
        new_message=content
    ):
        if event.is_final_response():
            assert event.content is not None
            assert len(event.content.parts) > 0
            final_response_text = event.content.parts[0].text

    # Check that the agent's response contains the key details.
    intents_to_check = [
        "Ishan Chauhan",
        "Ishank Gupta"
    ]
    assert await assert_intents_present(final_response_text, intents_to_check)



@pytest.mark.asyncio
async def test_hrms_agent_with_dashboard_mock(mock_mcp_connections, mock_mcp_auth):
    """Test HRMS agent with mocked dashboard tool."""
    from app.helpers.hrms_agent import initiate_hrms_agent
    
    agent = await initiate_hrms_agent()
    assert isinstance(agent, LlmAgent)
    
    # Test agent with a mock query
    from google.genai import types
    from google.adk.runners import Runner
    
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="hrms_agent",
        user_id="test_user",
        session_id="test_session_dashboard"
    )
    
    runner = Runner(
        agent=agent,
        app_name="hrms_agent",
        session_service=session_service
    )
    
    content = types.Content(role='user', parts=[types.Part(text="Show me the dashboard information for today")])
    
    final_response_text = ""
    async for event in runner.run_async(
        user_id="test_user",
        session_id="test_session_dashboard",
        new_message=content
    ):
        if event.is_final_response():
            assert event.content is not None
            assert len(event.content.parts) > 0
            final_response_text = event.content.parts[0].text

    # Check that the agent's response contains the key dashboard information.
    intents_to_check = [
        "the total number of employees is 150",
        "the Engineering department is mentioned",
        "the total number of people working from office is 100",
        "the total number of people working from home is 40"
    ]
    assert await assert_intents_present(final_response_text, intents_to_check)
