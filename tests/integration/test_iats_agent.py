import pytest
from unittest.mock import MagicMock, AsyncMock
from app.helpers.iats import initiate_iats_agent
from google.adk.sessions import InMemorySessionService, Session
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.llm_agent import LlmAgent
from google.genai import types
from tests.integration.fixtures.mcp_fixtures import mock_mcp_connections, mock_mcp_auth
from tests.utils.llm_assert import assert_intents_present


@pytest.mark.asyncio
async def test_iats_agent_basic_greeting(monkeypatch, mock_mcp_connections, mock_mcp_auth):
    """
    Tests that the interface ATS agent provides a basic greeting for a simple query
    without invoking any sub-agents or tools.
    """
    # 1. Mock the `safe_run_agent` function to return no sub-agents.
    #    This isolates the triage agent for the test.
    async def mock_safe_run_agent(*args, **kwargs):
        print("Mocked safe_run_agent called, returning no agents.")
        return []
    
    monkeypatch.setattr("app.helpers.iats.safe_run_agent", mock_safe_run_agent)

    # 2. Mock the DatabaseSessionService to use a faster in-memory version.
    #    The original code passes a `db_url` argument, which InMemorySessionService
    #    doesn't accept. We use a lambda to swallow this argument and return
    #    the in-memory service instance.
    monkeypatch.setattr(
        "app.helpers.iats.DatabaseSessionService",
        lambda *args, **kwargs: InMemorySessionService()
    )

    # 3. Call the triage agent with a simple greeting.
    query = "Hi, how are you?"
    response = await initiate_iats_agent(
        query=query,
        query_id="test_greeting_query_id",
        chat=query,
        profile_info={"email": "test@example.com"}
    )

    # 4. Assert the response using the LLM-based assertion tool.
    assert await assert_intents_present(response, ["a greeting and an offer of assistance"])

    print(f"\nAgent greeting response: {response}")

@pytest.mark.asyncio
async def test_iats_agent_fetch_job_profile(monkeypatch, mock_mcp_connections, mock_mcp_auth):
    """
    Tests that the iats agent correctly fetches job profile
    by using the real sub-agent implementations with mocked MCP connections.
    """
    # 1. Mock the DatabaseSessionService.
    monkeypatch.setattr(
        "app.helpers.iats.DatabaseSessionService",
        lambda *args, **kwargs: InMemorySessionService()
    )
    
    query = "show me job profile for the job title 'Software Engineer'"
    response = await initiate_iats_agent(
        query=query,
        query_id="test_iats_fetch_job_profile_query",
        chat=query,
        profile_info={"email": "test@example.com"}
    )
    # 4. Assert that the final response contains the key information.
    intents_to_check = [
        "job title is Software Engineer",
        "location is New York",
        "Skills include Python and java"
    ]
    assert await assert_intents_present(response, intents_to_check)

