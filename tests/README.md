# Testing Documentation

This directory contains the test suite for the project. The tests are organized into different categories to ensure comprehensive coverage of the codebase.

## Directory Structure

```
tests/
├── integration/        # Integration tests
│   ├── fixtures/      # Test fixtures and setup
│   │   ├── mcp_fixtures.py          # Mocks for MCP connections & auth
│   │   ├── hrms_fixtures.py         # Main fixture for HRMS mock toolset
│   │   ├── hrms_tool_mocks/         # Individual mock tools for HRMS
│   │   ├── story_fixtures.py        # Main fixture for Story mock toolset
│   │   ├── story_tool_mocks/        # Individual mock tools for Story
│   │   ├── ats_fixtures.py          # Main fixture for ATS mock toolset
│   │   ├── ats_tool_mocks/          # Individual mock tools for ATS
│   │   ├── calling_fixtures.py      # Main fixture for Calling mock toolset
│   │   └── calling_tool_mocks/      # Individual mock tools for Calling
│   ├── utils/         # Test utilities
│   └── expectations/  # Expected test outcomes
└── unit/              # Unit tests (if applicable)
```

## Running Tests

### Prerequisites

- Python 3.x
- UV (Python package installer and runner)
- pytest

### Environment Setup

Before running tests, ensure you have all dependencies installed:

```bash
uv pip install -r requirements.txt
```

### Running All Tests

To run all tests with detailed output:

```bash
PYTHONPATH=. PYTHONASYNCIODEBUG=1 uv run pytest -v -s tests/
```

### Running Specific Test Categories

Run integration tests only:
```bash
PYTHONPATH=. PYTHONASYNCIODEBUG=1 uv run pytest -v -s tests/integration/
```

### Test Command Options

- `-v`: Verbose output
- `-s`: Show print statements (don't capture stdout)
- `-k "test_name"`: Run tests matching the given name
- `--pdb`: Drop into debugger on test failures
- `--cov`: Generate coverage report (requires pytest-cov)

## Writing New Tests

### Integration Tests

1. Create a new test file in `tests/integration/` with a `test_` prefix.
2. For tests involving agents with external dependencies, see the **Agent Integration Testing Strategy** and **Maintaining Mock Toolsets** sections below for the preferred approach.
3. Use `pytest` fixtures for common setup and `async` test functions for asynchronous code.
    ```python
    import pytest

    @pytest.mark.asyncio
    async def test_your_feature(your_fixture):
        # Your test code here
        assert True
    ```
4. For complex event validation, you can add expected sequence patterns in `tests/integration/expectations/`.

### Test Utilities

- `assert_valid_response()`: Validates agent responses
- `validate_event_sequence()`: Verifies event sequences
- `print_session_events()`: Debug utility for session events

## Maintaining Mock Toolsets

The mock toolsets in `tests/integration/fixtures/` are designed to emulate the real tools available on the various MCP servers (HRMS, ATS, etc.). To keep the integration tests accurate, it's crucial to update these mocks whenever the real tools are changed.

### Mock Tool Structure

- **Main Fixture Files**: Files like `hrms_fixtures.py`, `ats_fixtures.py`, etc., are the entry points. They define the `Mock*Toolset` class that collects all the individual mock tools for a specific service.
- **Mock Tool Directories**: Each service has a corresponding `*_tool_mocks/` directory (e.g., `hrms_tool_mocks/`). This directory contains individual Python files, each defining a single mock tool class (e.g., `MockGetEmployeeDetailTool`).

### How to Update Mocks

#### When a Tool is Modified:
If a tool on a live MCP server is updated (e.g., its name, description, arguments, or return value changes):
1.  Navigate to the appropriate directory (e.g., `tests/integration/fixtures/hrms_tool_mocks/`).
2.  Find the Python file corresponding to the tool you need to update (e.g., `get_employee_detail.py`).
3.  Modify the `Mock*Tool` class within that file to reflect the changes. Pay close attention to the `_name`, `_description`, `_mcp_tool.inputSchema`, and the mock `__call__` method's return value.

#### When a New Tool is Added:
If a new tool is added to a live MCP server:
1.  Go to the relevant mocks directory (e.g., `tests/integration/fixtures/ats_tool_mocks/`).
2.  Create a new Python file for the new tool (e.g., `new_ats_tool.py`).
3.  Inside this file, create a new mock tool class (e.g., `MockNewAtsTool`) that inherits from `MCPTool`. Implement the `__init__`, `name`, `description`, `__call__`, and `run_async` methods to mimic the real tool.
4.  Open the main fixture file for that service (e.g., `ats_fixtures.py`).
5.  Import your new mock tool class: `from .ats_tool_mocks.new_ats_tool import MockNewAtsTool`.
6.  Add an instance of your new tool to the `_tools` list inside the `MockATSToolset` class.

By following these steps, you ensure the agent's integration tests remain a reliable reflection of its behavior with the live services.


## Environment Variables

The following environment variables are used in tests:

- `PYTHONPATH=.`: Ensures proper module imports
- `PYTHONASYNCIODEBUG=1`: Enables async debugging
- Additional environment variables may be required based on your configuration

## Agent Integration Testing Strategy

The primary strategy for integration testing agents that rely on external MCP (Model Context Protocol) services is to use the *real* agent implementations while mocking the connection to the MCP server. This provides a robust test that verifies the agent's internal logic, prompting, and tool-selection capabilities without the flakiness and overhead of running a live MCP server.

This is achieved through the `mock_mcp_connections` fixture located in `tests/integration/fixtures/mcp_fixtures.py`.

### How it Works

1. **`mock_mcp_connections` Fixture**: This `pytest` fixture patches the `connect_to_mcp_server` function within each agent's helper module (`app.helpers.*`).
2. **URL Matching**: When an agent attempts to initialize and connect to an MCP URL (e.g., `HRMS_MCP_URL`), the fixture intercepts this call. It checks the URL to determine which agent is being initialized.
3. **Mock Toolset Injection**: Based on the URL, the fixture returns a corresponding mock `MCPToolset` (e.g., `MockHRMSToolset` from `hrms_fixtures.py`). This mock toolset contains mock implementations of the tools that the real agent expects to find on the MCP server.
4. **Real Agent Logic**: The agent proceeds with its initialization, now equipped with mock tools. The test can then invoke the agent and assert that it correctly uses these tools and produces the expected final response.

### Example Usage

To use this in a test, simply include the `mock_mcp_connections` and `mock_mcp_auth` fixtures in your test function signature.

```python
import pytest
from app.helpers.triage import initiate_triage_agent
from google.adk.sessions import InMemorySessionService
from tests.integration.fixtures.mcp_fixtures import mock_mcp_connections, mock_mcp_auth


@pytest.mark.asyncio
async def test_triage_agent_routes_to_hrms(monkeypatch, mock_mcp_connections, mock_mcp_auth):
    """
    Tests that the triage agent correctly routes a query to the hrms_agent.
    """
    # 1. Mock other dependencies like the database
    monkeypatch.setattr(
        "app.helpers.triage.DatabaseSessionService",
        lambda *args, **kwargs: InMemorySessionService()
    )

    # 2. Call the agent. The fixtures will automatically handle mocking the MCPs.
    response = await initiate_triage_agent(
        query="Who is Jane Doe?",
        query_id="test_query",
        chat="Who is Jane Doe?",
        profile_info={"email": "test@example.com"}
    )

    # 3. Assert the response generated by the real agent using the mock tools.
    assert "jane.doe@kivo.ai" in response.lower()
```

## Best Practices

1. Each test function should test one specific functionality
2. Use descriptive test names that indicate what is being tested
3. Include appropriate assertions and validations
4. Add comments explaining complex test scenarios
5. Use fixtures for common setup and teardown
6. Handle async operations correctly with `@pytest.mark.asyncio`

## Troubleshooting

Common issues and solutions:

1. Import errors:
   - Ensure `PYTHONPATH` is set correctly
   - Check for circular imports

2. Async test failures:
   - Verify `@pytest.mark.asyncio` decorator is used
   - Check for proper await statements

3. Event sequence validation failures:
   - Review expected sequence patterns
   - Check event order and content 