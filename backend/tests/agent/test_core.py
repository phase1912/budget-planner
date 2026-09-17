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
        num_retries=3,
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


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_disable_reasoning_puts_reasoning_effort_in_extra_body(
    mock_acompletion: MagicMock,
) -> None:
    # Given
    agent = Agent(model="test-model", disable_reasoning=True)
    messages = [Message(role="user", content="Extract this")]

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"name": "test", "value": 42}'

    mock_acompletion.return_value = mock_response

    # When
    await agent.run_structured(messages, schema=MockSchema)

    # Then
    assert mock_acompletion.call_args.kwargs["extra_body"] == {"reasoning_effort": "none"}


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_hosted_provider_is_not_sent_the_reasoning_parameter(
    mock_acompletion: MagicMock,
) -> None:
    # Given
    agent = Agent(model="test-model")
    messages = [Message(role="user", content="Extract this")]

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"name": "test", "value": 42}'

    mock_acompletion.return_value = mock_response

    # When
    await agent.run_structured(messages, schema=MockSchema)

    # Then
    assert "extra_body" not in mock_acompletion.call_args.kwargs


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_answer_hidden_in_reasoning_channel_names_the_setting(
    mock_acompletion: MagicMock,
) -> None:
    # Given
    agent = Agent(model="test-model")
    messages = [Message(role="user", content="Extract this")]

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = ""
    mock_response.choices[0].message.reasoning_content = '{"name": "test", "value": 42}'

    mock_acompletion.return_value = mock_response

    # When / Then
    with pytest.raises(AgentError, match="LLM_DISABLE_REASONING"):
        await agent.run_structured(messages, schema=MockSchema)


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_disable_json_schema_omits_response_format(mock_acompletion: MagicMock) -> None:
    # Given
    agent = Agent(model="test-model", disable_json_schema=True)
    messages = [Message(role="user", content="Extract this")]

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"name": "test", "value": 42}'

    mock_acompletion.return_value = mock_response

    # When
    result = await agent.run_structured(messages, schema=MockSchema)

    # Then
    assert "response_format" not in mock_acompletion.call_args.kwargs
    assert result.name == "test"


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_schema_is_enforced_natively_by_default(mock_acompletion: MagicMock) -> None:
    # Given
    agent = Agent(model="test-model")
    messages = [Message(role="user", content="Extract this")]

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"name": "test", "value": 42}'

    mock_acompletion.return_value = mock_response

    # When
    await agent.run_structured(messages, schema=MockSchema)

    # Then
    response_format = mock_acompletion.call_args.kwargs["response_format"]
    assert response_format["json_schema"]["name"] == "MockSchema"
