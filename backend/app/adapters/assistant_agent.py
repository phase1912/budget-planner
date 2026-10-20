"""The assistant over the LiteLLM agent (F21.1, ADR-0006, ADR-0025).

Tools are offered by description and called through structured output, not a provider's
own tool-calling: every model the agent can reach — a hosted one or a small local one —
answers the same JSON, so the assistant works wherever receipts are read.
"""

import json
import logging
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, Field

from app.agent.core import Agent, AgentError
from app.agent.types import Message
from app.ports.assistant import (
    AssistantContext,
    AssistantPort,
    AssistantReply,
    ReadTool,
    ToolCall,
    ToolSpec,
    Turn,
)

logger = logging.getLogger(__name__)

MAX_STEPS = 4
"""Rounds of reading before the assistant must answer: a question needs one or two."""
HISTORY = 20
"""The latest messages the assistant reads back; older ones are not needed to go on."""
LANGUAGE_NAMES = {"en": "English", "uk": "Ukrainian", "pl": "Polish"}


class StepCall(BaseModel):
    """One tool the model asks for."""

    tool: str
    args: dict[str, Any] = Field(default_factory=dict)


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
        f"Answer in {language}, briefly and warmly, in plain words. Today is {context.today}; "
        f"money is in {context.currency}.\n"
        "You never change anything yourself. To record or change something, call a tool that "
        "proposes a card: the user checks it, may edit it and approves it. Say in one sentence "
        "what the card is; never claim it is saved. Words alone record nothing: every time "
        "the user asks to record or change something, call the tool again, even if a similar "
        "card was proposed before. Only a card the history marks as saved was saved.\n"
        "To answer about the user's money, call a read tool first and use only its numbers; "
        "never invent figures. Settings, the account and deleting anything are done on the "
        "screens, not by you: say so if asked.\n"
        f"Tools:\n{listed}\n"
        'Reply as JSON: {"say": "...", "calls": [{"tool": "name", "args": {...}}]}. '
        "Leave calls empty when you are only answering."
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
                step = await self._agent.run_structured(messages, Step, max_tokens=2048)
            except AgentError:
                logger.exception("The assistant's model call failed")
                return AssistantReply(said or "", proposals)
            said = step.say or said
            reads = []
            for call in step.calls:
                spec = known.get(call.tool)
                if spec is None:
                    continue
                if spec.writes:
                    proposals.append(ToolCall(call.tool, call.args))
                else:
                    reads.append(ToolCall(call.tool, call.args))
            if not reads:
                if not proposals and not read_any:
                    return await self._route(history, tools, context, said)
                return AssistantReply(said, proposals)
            read_any = True
            results = [f"{c.name}: {await read(c)}" for c in reads]
            messages.append(Message(role="assistant", content=step.model_dump_json()))
            messages.append(Message(role="user", content="Tool results:\n" + "\n".join(results)))
        return AssistantReply(said, proposals)

    async def _route(
        self,
        history: Sequence[Turn],
        tools: Sequence[ToolSpec],
        context: AssistantContext,
        said: str,
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
            )
        except AgentError:
            return AssistantReply(said)
        known = {t.name for t in writes}
        proposals = [ToolCall(c.tool, c.args) for c in step.calls if c.tool in known]
        if not proposals:
            return AssistantReply(said)
        return AssistantReply(step.say or said, proposals)
