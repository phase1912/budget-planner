"""The assistant over the model: reading, proposing, and surviving a failed call (F21.1)."""

from unittest.mock import AsyncMock

import pytest

from app.adapters.assistant_agent import AssistantAdapter, Step, StepCall
from app.agent.core import AgentError
from app.ports.assistant import AssistantContext, AssistantReply, ToolCall, ToolSpec, Turn

TOOLS = [
    ToolSpec("month_summary", "Spent this month.", {"properties": {}}, writes=False),
    ToolSpec("set_monthly_budget", "Propose a budget.", {"properties": {}}, writes=True),
]
CONTEXT = AssistantContext(language="pl", currency="PLN", today="2026-10-20")


@pytest.mark.asyncio
async def test_it_reads_first_and_answers_with_what_it_read() -> None:
    agent = AsyncMock()
    agent.run_structured.side_effect = [
        Step(say="", calls=[StepCall(tool="month_summary", args={})]),
        Step(say="Wydano 725 PLN.", calls=[]),
    ]
    read = AsyncMock(return_value='{"spent": "725.00"}')

    reply = await AssistantAdapter(agent).reply(
        [Turn("user", "Ile wydałem?")], TOOLS, read, CONTEXT
    )

    assert reply.text == "Wydano 725 PLN."
    assert reply.proposals == []
    read.assert_awaited_once_with(ToolCall("month_summary", {}))
    second_prompt = agent.run_structured.call_args_list[1].args[0]
    assert "725.00" in second_prompt[-1].content
    assert "Polish" in second_prompt[0].content


@pytest.mark.asyncio
async def test_a_write_only_comes_back_as_a_proposal_and_unknown_tools_are_dropped() -> None:
    agent = AsyncMock()
    agent.run_structured.return_value = Step(
        say="Here is the budget card.",
        calls=[
            StepCall(tool="set_monthly_budget", args={"amount": "2500"}),
            StepCall(tool="delete_account", args={}),
        ],
    )
    read = AsyncMock()

    reply = await AssistantAdapter(agent).reply([Turn("user", "Budget 2500")], TOOLS, read, CONTEXT)

    assert reply.proposals == [ToolCall("set_monthly_budget", {"amount": "2500"})]
    read.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_failed_model_call_ends_the_turn_without_raising() -> None:
    agent = AsyncMock()
    agent.run_structured.side_effect = AgentError("down")

    reply = await AssistantAdapter(agent).reply([Turn("user", "hi")], TOOLS, AsyncMock(), CONTEXT)

    assert (reply.text, reply.proposals) == ("", [])


@pytest.mark.asyncio
async def test_words_alone_for_a_request_get_a_second_look_that_proposes_its_card() -> None:
    """A small model may say "it is recorded" instead of proposing: nothing would be."""
    agent = AsyncMock()
    agent.run_structured.side_effect = [
        Step(say="It is recorded.", calls=[]),
        Step(
            say="Here is the card.",
            calls=[StepCall(tool="set_monthly_budget", args={"amount": "1"})],
        ),
    ]

    reply = await AssistantAdapter(agent).reply(
        [Turn("user", "Budget 1"), Turn("assistant", "(A card)"), Turn("user", "Budget 2")],
        TOOLS,
        AsyncMock(),
        CONTEXT,
    )

    assert reply == AssistantReply(
        "Here is the card.", [ToolCall("set_monthly_budget", {"amount": "1"})]
    )
    second = agent.run_structured.call_args_list[1].args[0]
    assert [m.content for m in second[1:]] == ["Budget 2"]


@pytest.mark.asyncio
async def test_second_look_returns_first_answer_when_agent_fails_or_makes_no_proposals() -> None:
    # Case 1: AgentError on second look
    agent = AsyncMock()
    agent.run_structured.side_effect = [
        Step(say="I see.", calls=[]),
        AgentError("timeout"),
    ]
    reply = await AssistantAdapter(agent).reply(
        [Turn("user", "Hello")], TOOLS, AsyncMock(), CONTEXT
    )
    assert reply == AssistantReply("I see.", [])

    # Case 2: No proposals on second look
    agent2 = AsyncMock()
    agent2.run_structured.side_effect = [
        Step(say="Just talking.", calls=[]),
        Step(say="Still talking.", calls=[]),
    ]
    reply2 = await AssistantAdapter(agent2).reply(
        [Turn("user", "Hello")], TOOLS, AsyncMock(), CONTEXT
    )
    assert reply2 == AssistantReply("Just talking.", [])

    # Case 3: No write tools offered
    agent3 = AsyncMock()
    read_only_tools = [ToolSpec("month_summary", "Summary", {"properties": {}}, writes=False)]
    agent3.run_structured.return_value = Step(say="Read only.", calls=[])
    reply3 = await AssistantAdapter(agent3).reply(
        [Turn("user", "Hello")], read_only_tools, AsyncMock(), CONTEXT
    )
    assert reply3 == AssistantReply("Read only.", [])
