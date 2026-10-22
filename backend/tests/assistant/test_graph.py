# ruff: noqa: RUF001 — the conversations here are in Russian and Ukrainian on purpose.
"""The assistant's graph over the model (F21.1, F21.13, ADR-0032): every tool is offered as
a function; reads answer at once, writes come back as checked proposals, `ask_user` ends
the turn with options, and a failed model call ends it without raising."""

from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.agent.core import AgentError
from app.agent.types import Message, ToolTurn, ToolUse
from app.assistant.core.graph import MAX_ROUNDS, THINKING_BUDGET, AssistantGraph
from app.assistant.core.language import language_of
from app.assistant.core.ports import AssistantContext, AssistantReply, ToolCall, ToolSpec, Turn

TOOLS = [
    ToolSpec("month_summary", "Spent this month.", {"type": "object", "properties": {}}, False),
    ToolSpec("set_monthly_budget", "Propose a budget.", {"type": "object", "properties": {}}, True),
    ToolSpec("stop_bill", "Stop a bill.", {"type": "object", "properties": {}}, True),
]
CONTEXT = AssistantContext(
    language="pl", currency="PLN", today="2026-10-20", known="Cards:\n  1. Main — card"
)


def turn(text: str = "", *calls: tuple[str, dict[str, Any]]) -> ToolTurn:
    """What the model does in one round: says `text` and calls `calls`."""
    uses = [ToolUse(f"c{i}", name, args) for i, (name, args) in enumerate(calls)]
    return ToolTurn(text, uses, Message(role="assistant", content=text))


def model(*turns: Any) -> AsyncMock:
    """A model that answers with `turns` in order."""
    agent = AsyncMock()
    agent.run_tools.side_effect = list(turns)
    return agent


def sent(agent: AsyncMock, call: int = 0) -> list[Message]:
    """The messages of the model's `call`-th request."""
    return list(agent.run_tools.call_args_list[call].args[0])


async def reply(agent: AsyncMock, said: str = "hi", **kwargs: Any) -> AssistantReply:
    return await AssistantGraph(agent).reply(
        [Turn("user", said)],
        TOOLS,
        kwargs.get("read", AsyncMock(return_value='{"spent": "725.00"}')),
        CONTEXT,
        kwargs.get("check"),
    )


@pytest.mark.asyncio
async def test_it_reads_first_and_answers_with_what_it_read() -> None:
    agent = model(turn("", ("month_summary", {})), turn("Wydano 725 PLN."))
    read = AsyncMock(return_value='{"spent": "725.00"}')

    answer = await reply(agent, "Ile wydałem?", read=read)

    assert answer == AssistantReply("Wydano 725 PLN.", [])
    read.assert_awaited_once_with(ToolCall("month_summary", {}))
    result = sent(agent, 1)[-1]
    assert (result.role, result.tool_call_id, result.content) == (
        "tool",
        "c0",
        '{"spent": "725.00"}',
    )


@pytest.mark.asyncio
async def test_every_tool_is_offered_as_a_function_with_ask_user_and_what_the_user_has() -> None:
    agent = model(turn("Cześć!"))

    await reply(agent, "hej")

    functions = agent.run_tools.call_args_list[0].args[1]
    assert [f["function"]["name"] for f in functions] == [
        "month_summary", "set_monthly_budget", "stop_bill", "ask_user",
    ]  # fmt: skip
    assert "Proposes a card" in functions[1]["function"]["description"]
    assert "1. Main — card" in str(sent(agent)[0].content)


@pytest.mark.asyncio
async def test_a_write_comes_back_as_a_proposal_and_the_model_is_told_it_is_not_saved() -> None:
    agent = model(
        turn("", ("set_monthly_budget", {"amount": "2500"}), ("delete_account", {})),
        turn("Here is the budget card."),
    )
    read = AsyncMock()

    answer = await reply(agent, "Budget 2500", read=read)

    assert answer == AssistantReply(
        "Here is the budget card.", [ToolCall("set_monthly_budget", {"amount": "2500"})]
    )
    read.assert_not_awaited()
    told = [m.content for m in sent(agent, 1)[-2:]]
    assert "not saved until they approve" in told[0] and "no tool delete_account" in told[1]


@pytest.mark.asyncio
async def test_asking_the_user_ends_the_turn_with_the_question_and_its_options() -> None:
    agent = model(
        turn("", ("ask_user", {"question": "Which card?", "options": ["Main", "Revolut"]}))
    )

    answer = await reply(agent, "update the balance")

    assert answer == AssistantReply("Which card?", [], ["Main", "Revolut"])
    assert agent.run_tools.await_count == 1


@pytest.mark.asyncio
async def test_a_refused_write_goes_back_with_why_and_its_words_are_not_shown() -> None:
    agent = model(
        turn("Here is the card.", ("set_monthly_budget", {"amount": "lots"})),
        turn("", ("set_monthly_budget", {"amount": 2500})),
        turn(""),
    )

    async def check(call: ToolCall) -> str | None:
        return None if isinstance(call.args.get("amount"), int) else "amount: not a number"

    answer = await reply(agent, "Budżet 2500", check=check)

    assert answer == AssistantReply("", [ToolCall("set_monthly_budget", {"amount": 2500})])
    assert "amount: not a number" in str(sent(agent, 1)[-1].content)


@pytest.mark.asyncio
async def test_a_failed_model_call_ends_the_turn_without_raising() -> None:
    answer = await reply(model(AgentError("down")))

    assert answer == AssistantReply("", [])


@pytest.mark.asyncio
async def test_a_model_that_keeps_calling_is_stopped_after_the_last_round() -> None:
    agent = model(*[turn("looking", ("month_summary", {}))] * (MAX_ROUNDS + 2))

    answer = await reply(agent)

    assert agent.run_tools.await_count == MAX_ROUNDS
    assert answer.text == "looking"


@pytest.mark.asyncio
async def test_every_round_gives_the_model_a_bounded_time_to_think() -> None:
    agent = model(turn("", ("month_summary", {})), turn("ok"))

    await reply(agent)

    budgets = [c.kwargs["thinking_budget"] for c in agent.run_tools.call_args_list]
    assert budgets == [THINKING_BUDGET] * 2


@pytest.mark.asyncio
async def test_the_conversation_so_far_is_read_back_and_the_answer_is_in_its_language() -> None:
    """ "2500" alone asks nothing; after "to how much?" it is the budget, in Russian."""
    agent = model(turn("Вот.", ("set_monthly_budget", {"amount": 2500})), turn("Вот."))

    await AssistantGraph(agent).reply(
        [
            Turn("user", "можешь поменять бюджет?"),
            Turn("assistant", "На какую сумму?"),
            Turn("user", "2500"),
        ],
        TOOLS,
        AsyncMock(),
        CONTEXT,
    )

    messages = sent(agent)
    assert [m.content for m in messages[1:]] == [
        "можешь поменять бюджет?",
        "На какую сумму?",
        "2500",
    ]
    assert "The user's last message is in Russian" in str(messages[0].content)


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
