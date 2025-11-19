import pytest
from unittest.mock import MagicMock

# Import the mock toolsets from other fixture files
from tests.integration.fixtures.hrms_fixtures import MockHRMSToolset
from tests.integration.fixtures.story_fixtures import MockStoryToolset
from tests.integration.fixtures.ats_fixtures import MockATSToolset
from tests.integration.fixtures.calling_fixtures import MockCallingToolset
from tests.integration.fixtures.iats_fixtures import MockIATSToolset

# Import the real constants to ensure the mock matches reality
from app.core.constants import (
    HRMS_MCP_SERVER_URL,
    PM_BOARD_MCP_URL,
    ATS_MCP_SERVER_URL,
    CALLING_MCP_SERVER_URL,
    IATS_MCP_SERVER_URL,
)

@pytest.fixture
def mock_mcp_connections(monkeypatch):
    """
    A master fixture that mocks all MCP connections for the triage agent's
    sub-agents. It inspects the server URL and returns the appropriate
    mock toolset.
    """
    async def mock_connect_to_mcp_server(server_url: str, *args, **kwargs):
        if server_url == HRMS_MCP_SERVER_URL:
            return MockHRMSToolset()
        if server_url == PM_BOARD_MCP_URL:
            return MockStoryToolset()
        if server_url == ATS_MCP_SERVER_URL:
            return MockATSToolset()
        if server_url == CALLING_MCP_SERVER_URL:
            return MockCallingToolset()
        if server_url == IATS_MCP_SERVER_URL:
            return MockIATSToolset()
        # Return None or raise an error for any unexpected connections
        return None

    # Patch the connect_to_mcp_server function in each agent helper module
    # where it is imported and called.
    monkeypatch.setattr(
        "app.helpers.hrms_agent.connect_to_mcp_server",
        mock_connect_to_mcp_server
    )
    monkeypatch.setattr(
        "app.helpers.pm_board_story_agent.connect_to_mcp_server",
        mock_connect_to_mcp_server
    )
    monkeypatch.setattr(
        "app.helpers.ats_agent.connect_to_mcp_server",
        mock_connect_to_mcp_server
    )
    monkeypatch.setattr(
        "app.helpers.calling_agent.connect_to_mcp_server",
        mock_connect_to_mcp_server
    )
    monkeypatch.setattr(
        "app.helpers.iats.connect_to_mcp_server",
        mock_connect_to_mcp_server
    )
    
    return mock_connect_to_mcp_server

@pytest.fixture
def mock_mcp_auth(monkeypatch):
    """Fixture that mocks MCP authentication for all servers."""
    
    async def mock_authenticate_mcp_servers():
        return "mock_token", "mock_public_key"
    
    monkeypatch.setattr(
        "app.services.mcp_auth.authenticate_mcp_servers",
        mock_authenticate_mcp_servers
    )
    
    class MockBearerAuthProvider:
        def __init__(self, *args, **kwargs): pass
        def create_token(self, *args, **kwargs): return "mock_token"
    
    monkeypatch.setattr(
        "fastmcp.server.auth.BearerAuthProvider",
        MockBearerAuthProvider
    )
    
    class MockRSAKeyPair:
        def __init__(self, *args, **kwargs): pass
        def create_token(self, *args, **kwargs): return "mock_token"
        @classmethod
        def generate(cls): return cls()
    
    monkeypatch.setattr(
        "fastmcp.server.auth.providers.bearer.RSAKeyPair",
        MockRSAKeyPair
    )
    
    return mock_authenticate_mcp_servers 