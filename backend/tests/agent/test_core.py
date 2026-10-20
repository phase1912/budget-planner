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


def _reply(content: str) -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    return response


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_without_native_schema_the_prompt_asks_for_bare_json(
    mock_acompletion: MagicMock,
) -> None:
    """A local model given no schema answered the categoriser in markdown prose."""
    mock_acompletion.return_value = _reply('{"name": "test", "value": 42}')
    agent = Agent(model="test-model", disable_json_schema=True)

    await agent.run_structured([Message(role="user", content="Categorise")], schema=MockSchema)

    sent = mock_acompletion.call_args.kwargs["messages"]
    assert sent[0] == {"role": "user", "content": "Categorise"}
    instruction = sent[-1]["content"]
    assert "JSON Schema" in instruction
    assert '"value"' in instruction


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_with_native_schema_the_prompt_is_left_alone(mock_acompletion: MagicMock) -> None:
    mock_acompletion.return_value = _reply('{"name": "test", "value": 42}')
    agent = Agent(model="test-model")

    await agent.run_structured([Message(role="user", content="Categorise")], schema=MockSchema)

    assert mock_acompletion.call_args.kwargs["messages"] == [
        {"role": "user", "content": "Categorise"}
    ]


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_json_wrapped_in_a_sentence_is_still_read(mock_acompletion: MagicMock) -> None:
    mock_acompletion.return_value = _reply(
        'Here is the result:\n{"name": "test", "value": 42}\nLet me know if you need more.'
    )
    agent = Agent(model="test-model", disable_json_schema=True)

    result = await agent.run_structured([Message(role="user", content="x")], schema=MockSchema)

    assert (result.name, result.value) == ("test", 42)


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_prose_with_no_json_at_all_is_still_an_error(mock_acompletion: MagicMock) -> None:
    mock_acompletion.return_value = _reply("### Analysis\n1. Item 0 is a mug, so Groceries.")
    agent = Agent(model="test-model", disable_json_schema=True)

    with pytest.raises(AgentError, match="Failed to parse LLM response as JSON"):
        await agent.run_structured([Message(role="user", content="x")], schema=MockSchema)


def _answer(content: str, finish_reason: str = "stop") -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    response.choices[0].finish_reason = finish_reason
    return response


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_a_receipt_is_read_by_gemini_without_thinking_first(
    mock_acompletion: MagicMock,
) -> None:
    """Gemini's thoughts share max_tokens with the answer and cut receipt JSON off."""
    mock_acompletion.return_value = _answer('{"name": "test", "value": 42}')
    messages = [Message(role="user", content="Extract this")]

    await Agent(model="vertex_ai/gemini-2.5-flash").run_structured(
        messages, schema=MockSchema, reasoning=False
    )
    await Agent(model="vertex_ai/gemini-2.5-flash").run_structured(messages, schema=MockSchema)
    await Agent(model="anthropic/claude-sonnet").run_structured(
        messages, schema=MockSchema, reasoning=False
    )

    calls = [call.kwargs for call in mock_acompletion.call_args_list]
    assert calls[0]["reasoning_effort"] == "disable"
    assert "reasoning_effort" not in calls[1]
    assert "reasoning_effort" not in calls[2]


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_a_thinking_budget_is_added_to_the_answers_room_not_taken_from_it(
    mock_acompletion: MagicMock,
) -> None:
    """Thoughts bounded and on top of the limit can no longer cut the JSON off (F15.5)."""
    mock_acompletion.return_value = _answer('{"name": "test", "value": 42}')
    messages = [Message(role="user", content="Extract this")]

    await Agent(model="vertex_ai/gemini-2.5-flash").run_structured(
        messages, schema=MockSchema, max_tokens=8192, thinking_budget=2048
    )
    await Agent(model="openai/qwen/qwen3.5-9b").run_structured(
        messages, schema=MockSchema, max_tokens=8192, thinking_budget=2048
    )

    gemini, local = (call.kwargs for call in mock_acompletion.call_args_list)
    assert gemini["thinking"] == {"type": "enabled", "budget_tokens": 2048}
    assert gemini["max_tokens"] == 8192 + 2048
    assert "reasoning_effort" not in gemini
    assert "thinking" not in local
    assert local["max_tokens"] == 8192


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_an_answer_cut_off_at_the_token_limit_says_so(mock_acompletion: MagicMock) -> None:
    mock_acompletion.return_value = _answer('{"name": "unterminated', finish_reason="length")

    with pytest.raises(AgentError, match="cut off at max_tokens"):
        await Agent(model="test-model").run_structured(
            [Message(role="user", content="Extract this")], schema=MockSchema
        )
