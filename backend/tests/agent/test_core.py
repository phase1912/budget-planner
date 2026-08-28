from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from app.agent.core import Agent, AgentError
from app.agent.types import Message


class MockSchema(BaseModel):
    name: str
    value: int


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_agent_run_unstructured(mock_acompletion: MagicMock) -> None:
    # Given
    agent = Agent(model="test-model")
    messages = [Message(role="user", content="Hello")]

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hi there"

    mock_acompletion.return_value = mock_response

    # When
    result = await agent.run(messages)

    # Then
    assert result == "Hi there"
    mock_acompletion.assert_called_once_with(
        model="test-model",
        messages=[{"role": "user", "content": "Hello"}],
        temperature=0.0,
        max_tokens=32768,
    )


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_agent_run_structured(mock_acompletion: MagicMock) -> None:
    # Given
    agent = Agent(model="test-model")
    messages = [Message(role="user", content="Extract this")]

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"name": "test", "value": 42}'

    mock_acompletion.return_value = mock_response

    # When
    result = await agent.run_structured(messages, schema=MockSchema)

    # Then
    assert isinstance(result, MockSchema)
    assert result.name == "test"
    assert result.value == 42


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_agent_run_structured_strips_markdown_fences(mock_acompletion: MagicMock) -> None:
    # Given
    agent = Agent(model="test-model")
    messages = [Message(role="user", content="Extract this")]

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '```json\n{"name": "test", "value": 42}\n```'

    mock_acompletion.return_value = mock_response

    # When
    result = await agent.run_structured(messages, schema=MockSchema)

    # Then
    assert result.name == "test"
    assert result.value == 42


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_agent_run_structured_raises_on_invalid_json(mock_acompletion: MagicMock) -> None:
    # Given
    agent = Agent(model="test-model")
    messages = [Message(role="user", content="Extract this")]

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"name": "test", "value": "not-an-int"}'

    mock_acompletion.return_value = mock_response

    # When/Then
    with pytest.raises(AgentError) as exc:
        await agent.run_structured(messages, schema=MockSchema)

    assert "did not match schema" in str(exc.value)
