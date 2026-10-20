"""The assistant over the LiteLLM agent (F21.1, ADR-0006, ADR-0025).

Tools are offered by description and called through structured output, not a provider's
own tool-calling: every model the agent can reach — a hosted one or a small local one —
answers the same JSON, so the assistant works wherever receipts are read.
"""

import json
import logging
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.agent.core import Agent, AgentError
from app.agent.types import Message
from app.ports.assistant import (
    AssistantContext,
    AssistantPort,
    AssistantReply,
    CheckTool,
    ReadTool,
    ToolCall,
    ToolSpec,
    Turn,
)

logger = logging.getLogger(__name__)

MAX_STEPS = 4
"""Rounds of reading before the assistant must answer: a question needs one or two."""
HISTORY = 20
THINKING_BUDGET = 1024
"""What Gemini may think before each step, added on top of the answer's limit: left
unbounded, its thoughts filled the limit and the answer came back empty."""
"""The latest messages the assistant reads back; older ones are not needed to go on."""
LANGUAGE_NAMES = {"en": "English", "uk": "Ukrainian", "pl": "Polish"}
EXAMPLES = "Examples:\n" + "\n".join(
    f"{user!r} -> {json.dumps(answer, ensure_ascii=False)}"
    for user, answer in (
        (
            "можешь поменять бюджет трат в месяц на 2500",
            {
                "say": "Вот карточка: месячный бюджет 2500.",
                "calls": [{"tool": "set_monthly_budget", "args": '{"amount": 2500}'}],
            },
        ),
        ("поменяй месячный бюджет", {"say": "На какую сумму?", "calls": []}),  # noqa: RUF001
        (
            "Ile wydałem w tym miesiącu?",
            {"say": "", "calls": [{"tool": "month_summary", "args": "{}"}]},
        ),
        (
            "How much did I spend on groceries this month compared to last?",
            {
                "say": "",
                "calls": [{"tool": "spending_by_category", "args": '{"compare": true}'}],
            },
        ),
        (
            "Де найдешевше молоко?",
            {"say": "", "calls": [{"tool": "product_prices", "args": '{"name": "молоко"}'}]},
        ),
    )
)
"""A few answers shown whole: a small model follows an example better than a rule."""


class StepCall(BaseModel):
    """One tool the model asks for.

    Its arguments travel as a JSON string, not an open object: Gemini's structured output
    refuses a schema with free-form properties, and the whole answer was lost with it.
    """

    tool: str
    args: str = Field("{}", description="The tool's arguments as a JSON object")

    @field_validator("args", mode="before")
    @classmethod
    def _as_json(cls, value: Any) -> Any:
        return json.dumps(value) if isinstance(value, dict) else value

    def arguments(self) -> dict[str, Any]:
        """The arguments as a dict; anything that is not a JSON object reads as none."""
        try:
            parsed = json.loads(self.args or "{}")
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}


class Step(BaseModel):
    """What the model does next: say something, call tools, or both."""

    say: str = Field("", description="What to tell the user now")
    calls: list[StepCall] = Field(default_factory=list)


def _system(tools: Sequence[ToolSpec], context: AssistantContext) -> str:
    listed = "\n".join(
        f"- {t.name} ({'proposes a card' if t.writes else 'reads data'}): {t.description} "
        f"Arguments: {json.dumps(t.parameters.get('properties', {}))}"
        for t in tools
    )
    language = LANGUAGE_NAMES.get(context.language, "English")
    return (
        "You are the assistant of a family budgeting app built on receipts read line by line. "
        "Always answer in the language of the user's last message (Russian to Russian, "
        f"Ukrainian to Ukrainian); only if it is unclear, in {language}. Be brief and warm, "
        f"in plain words. Today is {context.today}; "
        f"money is in {context.currency}. Resolve days like 'yesterday' from today.\n"
        + (
            f"The user's spending categories: {', '.join(context.categories)}. Pick the "
            "closest for each expense.\n"
            if context.categories
            else ""
        )
        + "Several things in one message become several calls, one card each.\n"
        "You never change anything yourself. To record or change something, call a tool that "
        "proposes a card: the user checks it, may edit it and approves it. Say in one sentence "
        "what the card is; never claim it is saved. Words alone record nothing: every time "
        "the user asks to record or change something, call the tool again, even if a similar "
        "card was proposed before. Only a card the history marks as saved was saved.\n"
        "To answer about the user's money, call a read tool first and use only its numbers; "
        "never invent figures. A chart or a link to the screen is shown below your answer by "
        "itself: do not describe it, say the figures that answer the question.\n"
        "Settings, the account and deleting anything are done on the "
        "screens, not by you: say so if asked. Amounts are plain numbers like 2500 or 12.50, "
        "without spaces or currency.\n"
        f"Tools:\n{listed}\n"
        'Reply as JSON: {"say": "...", "calls": [{"tool": "name", "args": "{...}"}]}, with '
        "args the tool's arguments as a JSON string. Leave calls empty when only answering.\n"
        + EXAMPLES
    )


class AssistantAdapter(AssistantPort):
    """Answers through the agent, reading with tools until it can say something."""

    def __init__(self, agent: Agent) -> None:
        self._agent = agent

    async def reply(
        self,
        history: Sequence[Turn],
        tools: Sequence[ToolSpec],
        read: ReadTool,
        context: AssistantContext,
        check: CheckTool | None = None,
    ) -> AssistantReply:
        known = {t.name: t for t in tools}
        messages = [Message(role="system", content=_system(tools, context))] + [
            Message(role=turn.role, content=turn.text) for turn in history[-HISTORY:]
        ]
        proposals: list[ToolCall] = []
        said = ""
        read_any = False
        for _ in range(MAX_STEPS):
            try:
                step = await self._agent.run_structured(
                    messages, Step, max_tokens=2048, thinking_budget=THINKING_BUDGET
                )
            except AgentError:
                logger.exception("The assistant's model call failed")
                return AssistantReply(said or "", proposals)
            said = step.say or said
            reads: list[ToolCall] = []
            wrong: list[str] = []
            for call in step.calls:
                spec = known.get(call.tool)
                if spec is None:
                    continue
                asked = ToolCall(call.tool, call.arguments())
                if not spec.writes:
                    reads.append(asked)
                elif error := (check(asked) if check else None):
                    wrong.append(f"{asked.name}: {error}")
                else:
                    proposals.append(asked)
            if not reads and not wrong:
                if not proposals and not read_any:
                    return await self._route(history, tools, context, said, check)
                return AssistantReply(said, proposals)
            read_any = True
            results = [f"{c.name}: {await read(c)}" for c in reads]
            results += [f"{w} — call it again with fixed arguments" for w in wrong]
            messages.append(Message(role="assistant", content=step.model_dump_json()))
            messages.append(Message(role="user", content="Tool results:\n" + "\n".join(results)))
        return AssistantReply(said, proposals)

    async def _route(
        self,
        history: Sequence[Turn],
        tools: Sequence[ToolSpec],
        context: AssistantContext,
        said: str,
        check: CheckTool | None,
    ) -> AssistantReply:
        """A second look at the user's last message alone, when the answer was words only.

        With a long history a small model may answer "it is recorded" instead of proposing a
        card. Read on its own, the request is told apart reliably: if it asks to record or
        change something, its card is proposed; otherwise the first answer stands.
        """
        last = next((t.text for t in reversed(history) if t.role == "user"), "")
        writes = [t for t in tools if t.writes]
        if not last or not writes:
            return AssistantReply(said)
        try:
            step = await self._agent.run_structured(
                [
                    Message(role="system", content=_system(writes, context)),
                    Message(role="user", content=last),
                ],
                Step,
                max_tokens=1024,
                thinking_budget=THINKING_BUDGET,
            )
        except AgentError:
            return AssistantReply(said)
        known = {t.name for t in writes}
        asked = [ToolCall(c.tool, c.arguments()) for c in step.calls if c.tool in known]
        proposals = [c for c in asked if not (check and check(c))]
        if not proposals:
            return AssistantReply(said)
        return AssistantReply(step.say or said, proposals)
