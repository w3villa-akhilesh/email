import pytest
from unittest.mock import MagicMock, AsyncMock
from app.helpers.triage import initiate_triage_agent
from google.adk.sessions import InMemorySessionService
from google.adk.agents.llm_agent import LlmAgent
from google.genai import types
from tests.integration.fixtures.mcp_fixtures import mock_mcp_connections, mock_mcp_auth
from tests.utils.llm_assert import assert_intents_present

@pytest.mark.asyncio
async def test_triage_agent_basic_greeting(monkeypatch):
    """
    Tests that the triage agent provides a basic greeting for a simple query
    without invoking any sub-agents.
    """
    # 1. Mock the `safe_run_agent` function to return no sub-agents.
    #    This isolates the triage agent for the test.
    async def mock_safe_run_agent(*args, **kwargs):
        print("Mocked safe_run_agent called, returning no agents.")
        return []
    
    monkeypatch.setattr("app.helpers.triage.safe_run_agent", mock_safe_run_agent)

    # 2. Mock the DatabaseSessionService to use a faster in-memory version.
    #    The original code passes a `db_url` argument, which InMemorySessionService
    #    doesn't accept. We use a lambda to swallow this argument and return
    #    the in-memory service instance.
    monkeypatch.setattr(
        "app.helpers.triage.DatabaseSessionService",
        lambda *args, **kwargs: InMemorySessionService()
    )

    # 3. Call the triage agent with a simple greeting.
    query = "Hi, how are you?"
    response = await initiate_triage_agent(
        query=query,
        query_id="test_greeting_query_id",
        chat=query,
        profile_info={"email": "test@example.com"}
    )

    # 4. Assert the response using the LLM-based assertion tool.
    assert await assert_intents_present(response, ["a greeting and an offer of assistance"])

    print(f"\nAgent greeting response: {response}")

@pytest.mark.asyncio
async def test_triage_agent_routes_to_hrms(monkeypatch, mock_mcp_connections, mock_mcp_auth):
    """
    Tests that the triage agent correctly routes a query to the hrms_agent
    by using the real sub-agent implementations with mocked MCP connections.
    """
    # 1. Mock the DatabaseSessionService.
    monkeypatch.setattr(
        "app.helpers.triage.DatabaseSessionService",
        lambda *args, **kwargs: InMemorySessionService()
    )
    monkeypatch.setattr("app.helpers.triage.ALLOWED_CALLING_EMAILS", ["test@example.com"])

    # 2. Call the triage agent with an HRMS-specific query.
    #    The mock_mcp_connections fixture will intercept the MCP calls
    #    made by the real sub-agent initializers.
    query = "Who is Jane Doe?"
    response = await initiate_triage_agent(
        query=query,
        query_id="test_hrms_route_query",
        chat=query,
        profile_info={"email": "test@example.com"}
    )
    # 4. Assert that the final response contains the key information.
    intents_to_check = [
        "Jane Doe",
        "jane.doe@kivo.ai",
        "1234567890"
    ]
    assert await assert_intents_present(response, intents_to_check) 

@pytest.mark.asyncio
async def test_triage_agent_routes_to_link_generation_agent(monkeypatch, mock_mcp_connections, mock_mcp_auth):
    """
    Tests that the triage agent correctly routes a query to the link_generation_agent
    by using the real sub-agent implementations with mocked MCP connections.
    """
    # 1. Mock the DatabaseSessionService.
    monkeypatch.setattr(
        "app.helpers.triage.DatabaseSessionService",
        lambda *args, **kwargs: InMemorySessionService()
    )
    monkeypatch.setattr("app.helpers.triage.ALLOWED_CALLING_EMAILS", ["test@example.com"])

    # 2. Call the triage agent with an HRMS-specific query.
    #    The mock_mcp_connections fixture will intercept the MCP calls
    #    made by the real sub-agent initializers.
    query = "I need link for lms."
    response = await initiate_triage_agent(
        query=query,
        query_id="test_hrms_route_query",
        chat=query,
        profile_info={"email": "test@example.com"}
    )
    # 4. Assert that the final response contains the key information.
    intents_to_check = [
        "Here is the Link: 'https://demo-pms.kivo.ai' to the your required page."
    ]
    assert await assert_intents_present(response, intents_to_check) 
