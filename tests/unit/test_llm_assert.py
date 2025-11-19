import pytest
from tests.utils.llm_assert import assert_intent_equals, assert_intents_present
from unittest.mock import patch, MagicMock, AsyncMock
import json

@pytest.mark.asyncio
async def test_assert_intent_equals_same_intent():
    """
    Tests that the assert_intent_equals function returns True for statements
    with the same intent.
    """
    statement1 = "Can you please find the details for John Doe?"
    statement2 = "I need the information on John Doe."
    assert await assert_intent_equals(statement1, statement2) is True

@pytest.mark.asyncio
async def test_assert_intent_equals_different_intent():
    """
    Tests that the assert_intent_equals function returns False for statements
    with different intents.
    """
    statement1 = "What is the current weather in New York?"
    statement2 = "Show me the company's financial report."
    assert await assert_intent_equals(statement1, statement2) is False

@pytest.mark.asyncio
async def test_assert_intent_equals_subtly_different_intent():
    """
    Tests that the assert_intent_equals function returns False for statements
    with subtly different intents.
    """
    statement1 = "Show me the company's performance dashboard."
    statement2 = "Show me the team's performance dashboard."
    assert await assert_intent_equals(statement1, statement2) is False

@pytest.mark.asyncio
@patch('openai.AsyncOpenAI')
async def test_assert_intents_present_all_present(mock_async_openai):
    """
    Tests that `assert_intents_present` returns True when all intents are found.
    """
    # 1. Configure the mock
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    
    mock_message.content = json.dumps({
        "results": {
            "the user is asking for a project status": {"present": True},
            "the user mentioned the 'Kivo' project": {"present": True}
        }
    })
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    
    # Configure the mock client to return the mock response
    mock_async_openai.return_value.chat.completions.create = AsyncMock(return_value=mock_response)

    # 2. Define test data
    statement = "I need a status update on the Kivo project."
    intents = ["the user is asking for a project status", "the user mentioned the 'Kivo' project"]

    # 3. Run the assertion
    result = await assert_intents_present(statement, intents)
    
    # 4. Assert the outcome
    assert result is True
    mock_async_openai.return_value.chat.completions.create.assert_called_once()

@pytest.mark.asyncio
@patch('openai.AsyncOpenAI')
async def test_assert_intents_present_one_missing(mock_async_openai):
    """
    Tests that `assert_intents_present` returns False when one intent is missing.
    """
    # 1. Configure the mock
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    
    mock_message.content = json.dumps({
        "results": {
            "the user is asking for a project status": {"present": True},
            "the user mentioned the 'Kivo' project": {"present": False, "reason": "The project name 'Kivo' was not found."}
        }
    })
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    
    # Configure the mock client to return the mock response
    mock_async_openai.return_value.chat.completions.create = AsyncMock(return_value=mock_response)

    # 2. Define test data
    statement = "I need a status update on the project."
    intents = ["the user is asking for a project status", "the user mentioned the 'Kivo' project"]

    # 3. Run the assertion
    result = await assert_intents_present(statement, intents)
    
    # 4. Assert the outcome
    assert result is False
    mock_async_openai.return_value.chat.completions.create.assert_called_once() 