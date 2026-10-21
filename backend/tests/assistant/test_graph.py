"""The assistant's graph over the model: what a message wants decides the tools; it reads,
proposes, fixes a wrong call and survives a failed one (F21.1, F21.7)."""

from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.agent.core import AgentError
from app.assistant.core.graph import THINKING_BUDGET, AssistantGraph, Intents, Step, StepCall
from app.assistant.core.language import language_of
from app.assistant.core.ports import (
    AssistantContext,
    AssistantReply,
    Intent,
    ToolCall,
    ToolSpec,
    Turn,
)

TOOLS = [
    ToolSpec(
        "month_summary", "Spent this month.", {"properties": {}}, False, frozenset({Intent.ASK})
    ),
    ToolSpec(
        "set_monthly_budget",
        "Propose a budget.",
        {"properties": {}},
        True,
        frozenset({Intent.ADD, Intent.CHANGE}),
    ),
    ToolSpec("stop_bill", "Stop a bill.", {"properties": {}}, True, frozenset({Intent.REMOVE})),
]
CONTEXT = AssistantContext(language="pl", currency="PLN", today="2026-10-20")


def model(intents: list[str], *steps: Any) -> AsyncMock:
    """A model that names `intents` for the message, then answers with `steps` in turn."""
    agent = AsyncMock()
    agent.run_structured.side_effect = [Intents(intents=intents), *steps]
    return agent


def prompt(agent: AsyncMock, call: int = 1) -> str:
    """The system prompt of the model's `call`-th request."""
    return str(agent.run_structured.call_args_list[call].args[0][0].content)


def offered(agent: AsyncMock, call: int = 1) -> str:
    """The tools listed in that prompt, without the examples after them."""
    text = prompt(agent, call)
    return text.split("Reply as JSON")[0].split("Tools:")[-1]


@pytest.mark.asyncio
async def test_it_reads_first_and_answers_with_what_it_read() -> None:
    agent = model(
        ["ask"],
        Step(say="", calls=[StepCall(tool="month_summary", args={})]),
        Step(say="Wydano 725 PLN.", calls=[]),
    )
    read = AsyncMock(return_value='{"spent": "725.00"}')

    reply = await AssistantGraph(agent).reply([Turn("user", "Ile wydałem?")], TOOLS, read, CONTEXT)

    assert reply == AssistantReply("Wydano 725 PLN.", [])
    read.assert_awaited_once_with(ToolCall("month_summary", {}))
    assert "725.00" in agent.run_structured.call_args_list[2].args[0][-1].content
    assert "Polish" in prompt(agent)


@pytest.mark.asyncio
async def test_a_question_is_offered_read_tools_only_and_a_removal_its_own() -> None:
    asking = model(["ask"], Step(say="ok", calls=[]))
    removing = model(["remove"], Step(say="", calls=[StepCall(tool="stop_bill", args={})]))

    await AssistantGraph(asking).reply([Turn("user", "how much?")], TOOLS, AsyncMock(), CONTEXT)
    reply = await AssistantGraph(removing).reply(
        [Turn("user", "stop the gym")], TOOLS, AsyncMock(), CONTEXT
    )

    assert "month_summary" in offered(asking)
    assert "set_monthly_budget" not in offered(asking)
    assert "stop_bill" in offered(removing) and "month_summary" not in offered(removing)
    assert reply.proposals == [ToolCall("stop_bill", {})]


@pytest.mark.asyncio
async def test_small_talk_is_offered_no_tool_and_a_failed_guess_every_tool() -> None:
    talking = model([], Step(say="Cześć!", calls=[]))
    unsure = AsyncMock()
    unsure.run_structured.side_effect = [
        AgentError("down"),
        Step(say="ok", calls=[]),
        Step(say="ok", calls=[]),
    ]

    reply = await AssistantGraph(talking).reply([Turn("user", "hej")], TOOLS, AsyncMock(), CONTEXT)
    await AssistantGraph(unsure).reply([Turn("user", "hm")], TOOLS, AsyncMock(), CONTEXT)

    assert reply.text == "Cześć!"
    assert "There are no tools" in prompt(talking)
    assert all(name in offered(unsure) for name in ("month_summary", "stop_bill"))


@pytest.mark.asyncio
async def test_a_write_only_comes_back_as_a_proposal_and_unknown_tools_are_dropped() -> None:
    agent = model(
        ["change"],
        Step(
            say="Here is the budget card.",
            calls=[
                StepCall(tool="set_monthly_budget", args={"amount": "2500"}),
                StepCall(tool="delete_account", args={}),
            ],
        ),
    )
    read = AsyncMock()

    reply = await AssistantGraph(agent).reply([Turn("user", "Budget 2500")], TOOLS, read, CONTEXT)

    assert reply.proposals == [ToolCall("set_monthly_budget", {"amount": "2500"})]
    read.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_failed_model_call_ends_the_turn_without_raising() -> None:
    agent = model(["ask"], AgentError("down"))

    reply = await AssistantGraph(agent).reply([Turn("user", "hi")], TOOLS, AsyncMock(), CONTEXT)

    assert (reply.text, reply.proposals) == ("", [])


@pytest.mark.asyncio
async def test_words_alone_for_a_request_get_a_second_look_that_proposes_its_card() -> None:
    """A small model may say "it is recorded" instead of proposing: nothing would be."""
    agent = model(
        ["change"],
        Step(say="It is recorded.", calls=[]),
        Step(say="Here is the card.", calls=[StepCall(tool="set_monthly_budget", args={})]),
    )

    reply = await AssistantGraph(agent).reply(
        [Turn("user", "Budget 1"), Turn("assistant", "(A card)"), Turn("user", "Budget 2")],
        TOOLS,
        AsyncMock(),
        CONTEXT,
    )

    assert reply == AssistantReply("Here is the card.", [ToolCall("set_monthly_budget", {})])
    second = agent.run_structured.call_args_list[2].args[0]
    assert [m.content for m in second[1:]] == ["Budget 2"]


@pytest.mark.asyncio
async def test_no_second_look_for_a_question_or_when_it_finds_nothing() -> None:
    asking = model(["ask"], Step(say="I see.", calls=[]))
    failing = model(["add"], Step(say="I see.", calls=[]), AgentError("timeout"))
    empty = model(["add"], Step(say="Just talking.", calls=[]), Step(say="Still.", calls=[]))

    replies = [
        await AssistantGraph(m).reply([Turn("user", "Hello")], TOOLS, AsyncMock(), CONTEXT)
        for m in (asking, failing, empty)
    ]

    assert replies == [
        AssistantReply("I see.", []),
        AssistantReply("I see.", []),
        AssistantReply("Just talking.", []),
    ]
    assert asking.run_structured.await_count == 2


def test_tool_arguments_travel_as_a_json_string_with_no_open_object_in_the_schema() -> None:
    schema = Step.model_json_schema()
    assert schema["$defs"]["StepCall"]["properties"]["args"]["type"] == "string"
    assert StepCall(tool="t", args='{"amount": 2500}').arguments() == {"amount": 2500}
    assert StepCall(tool="t", args="not json").arguments() == {}


@pytest.mark.asyncio
async def test_a_write_with_wrong_arguments_goes_back_to_the_model_to_be_fixed() -> None:
    agent = model(
        ["change"],
        Step(say="", calls=[StepCall(tool="set_monthly_budget", args={"amount": "lots"})]),
        Step(say="Budżet.", calls=[StepCall(tool="set_monthly_budget", args={"amount": 2500})]),
    )

    async def check(call: ToolCall) -> str | None:
        return None if isinstance(call.args.get("amount"), int) else "amount: not a number"

    reply = await AssistantGraph(agent).reply(
        [Turn("user", "Budżet 2500")], TOOLS, AsyncMock(), CONTEXT, check
    )

    assert reply.proposals == [ToolCall("set_monthly_budget", {"amount": 2500})]
    assert "amount: not a number" in agent.run_structured.call_args_list[2].args[0][-1].content


@pytest.mark.asyncio
async def test_it_is_told_to_answer_in_the_language_the_user_wrote_in() -> None:
    agent = model(["ask"], Step(say="Привет", calls=[]))

    await AssistantGraph(agent).reply([Turn("user", "привет")], TOOLS, AsyncMock(), CONTEXT)

    assert "language of the user's last message" in prompt(agent)


@pytest.mark.asyncio
async def test_every_step_gives_the_model_a_bounded_time_to_think() -> None:
    agent = model(["add"], Step(say="Hi", calls=[]), Step(say="", calls=[]))

    await AssistantGraph(agent).reply([Turn("user", "hi")], TOOLS, AsyncMock(), CONTEXT)

    budgets = [c.kwargs["thinking_budget"] for c in agent.run_structured.call_args_list]
    assert budgets == [THINKING_BUDGET] * 3


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("хочу накопичити 5000 на відпустку", "Ukrainian"),
        ("сколько я потратил в этом месяце?", "Russian"),
        ("можешь поменять бюджет трат в месяц на 2500", "Russian"),
        ("поменяй месячный бюджет", "Russian"),
        ("постав бюджет 3000", "Ukrainian"),
        ("Chcę wydawać mniej na restauracje", "Polish"),
        ("ile wydalem w tym miesiacu", "Polish"),
        ("How much did I spend?", "English"),
        ("2500", "Polish"),
    ],
)
def test_the_language_of_a_message_is_told_by_its_letters(text: str, language: str) -> None:
    assert language_of(text, "Polish") == language


@pytest.mark.asyncio
async def test_the_model_is_told_by_name_which_language_to_answer_in() -> None:
    agent = model([], Step(say="ok", calls=[]))

    await AssistantGraph(agent).reply(
        [Turn("user", "хочу накопичити 5000")], TOOLS, AsyncMock(), CONTEXT
    )

    assert "The user's last message is in Ukrainian" in prompt(agent)
