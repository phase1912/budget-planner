"""The assistant as an agent graph (F21.1, F21.7, ADR-0025, ADR-0028).

Three steps, as LangGraph nodes: `classify` decides what the message wants, `act` lets
the model read and propose with only the tools that serve it — again, while it reads or
fixes a call — and `second_look` reads the request alone when a wish to write came back
as words only. Tools are offered by description and called through structured output, not
a provider's own tool-calling: every model the agent can reach — a hosted one or a small
local one — answers the same JSON.
"""

import json
import logging
from collections.abc import Sequence
from typing import Any, Literal, Protocol, TypedDict, TypeVar

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, field_validator

from app.agent.core import AgentError
from app.agent.types import Message
from app.assistant.core import prompts
from app.assistant.core.ports import (
    AssistantContext,
    AssistantPort,
    AssistantReply,
    CheckTool,
    Intent,
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
THINKING_BUDGET = 1024
"""What Gemini may think before each step, added on top of the answer's limit: left
unbounded, its thoughts filled the limit and the answer came back empty."""
WRITES = frozenset({Intent.ADD, Intent.CHANGE, Intent.REMOVE})

T = TypeVar("T", bound=BaseModel)


class StructuredModel(Protocol):
    """The model the graph asks: messages in, an instance of `schema` out (ADR-0006)."""

    async def run_structured(
        self,
        messages: list[Message],
        schema: type[T],
        *,
        max_tokens: int = ...,
        thinking_budget: int | None = ...,
    ) -> T: ...


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


class Intents(BaseModel):
    """What the user's message wants; none for small talk."""

    intents: list[Literal["ask", "add", "change", "remove"]] = Field(default_factory=list)


class State(TypedDict, total=False):
    """What the graph carries from one node to the next."""

    intents: frozenset[Intent]
    tools: list[ToolSpec]
    messages: list[Message]
    proposals: list[ToolCall]
    said: str
    read_any: bool
    steps: int
    more: bool


class AssistantGraph(AssistantPort):
    """Answers through the model, choosing tools by what the message wants."""

    def __init__(self, model: StructuredModel) -> None:
        self._model = model

    async def reply(
        self,
        history: Sequence[Turn],
        tools: Sequence[ToolSpec],
        read: ReadTool,
        context: AssistantContext,
        check: CheckTool | None = None,
    ) -> AssistantReply:
        last = next((t.text for t in reversed(history) if t.role == "user"), "")

        async def classify(state: State) -> State:
            intents = await self._intents(last, context)
            # "Spend less on X" is told as a change as often as an addition: the two are
            # offered together, so the right tool is there whichever was named.
            if intents & {Intent.ADD, Intent.CHANGE}:
                intents = intents | {Intent.ADD, Intent.CHANGE}
            offered = [t for t in tools if t.intents & intents] if intents else []
            messages = [Message(role="system", content=prompts.system(offered, context, last))] + [
                Message(role=turn.role, content=turn.text) for turn in history[-HISTORY:]
            ]
            return {"intents": intents, "tools": offered, "messages": messages}

        async def act(state: State) -> State:
            known = {t.name: t for t in state["tools"]}
            messages = list(state["messages"])
            proposals = list(state.get("proposals", []))
            try:
                step = await self._model.run_structured(
                    messages, Step, max_tokens=2048, thinking_budget=THINKING_BUDGET
                )
            except AgentError:
                logger.exception("The assistant's model call failed")
                return {"more": False}
            reads: list[ToolCall] = []
            wrong: list[str] = []
            for call in step.calls:
                spec = known.get(call.tool)
                if spec is None:
                    continue
                asked = ToolCall(call.tool, call.arguments())
                if not spec.writes:
                    reads.append(asked)
                elif error := (await check(asked) if check else None):
                    wrong.append(f"{asked.name}: {error}")
                else:
                    proposals.append(asked)
            said = step.say or state.get("said", "")
            if not reads and not wrong:
                return {"said": said, "proposals": proposals, "more": False}
            results = [f"{c.name}: {await read(c)}" for c in reads]
            results += [f"{w} — call it again with fixed arguments" for w in wrong]
            messages.append(Message(role="assistant", content=step.model_dump_json()))
            messages.append(Message(role="user", content="Tool results:\n" + "\n".join(results)))
            return {
                "said": said,
                "proposals": proposals,
                "messages": messages,
                "read_any": True,
                "steps": state.get("steps", 0) + 1,
                "more": state.get("steps", 0) + 1 < MAX_STEPS,
            }

        async def second_look(state: State) -> State:
            said, proposals = await self._second_look(last, state["tools"], context, check)
            if not proposals:
                return {}
            return {"said": said or state.get("said", ""), "proposals": proposals}

        def after_act(state: State) -> str:
            if state.get("more"):
                return "act"
            wanted_writes = bool(state.get("intents", frozenset()) & WRITES)
            if wanted_writes and not state.get("proposals") and not state.get("read_any"):
                return "second_look"
            return END

        graph = StateGraph(State)
        graph.add_node("classify", classify)
        graph.add_node("act", act)
        graph.add_node("second_look", second_look)
        graph.add_edge(START, "classify")
        graph.add_edge("classify", "act")
        graph.add_conditional_edges("act", after_act, ["act", "second_look", END])
        graph.add_edge("second_look", END)
        final: State = await graph.compile().ainvoke({})  # type: ignore[assignment]
        return AssistantReply(final.get("said", ""), list(final.get("proposals", [])))

    async def _intents(self, last: str, context: AssistantContext) -> frozenset[Intent]:
        """What the message wants; every intent when the model cannot say, so no tool
        the user needed is ever withheld for a failed guess."""
        if not last:
            return frozenset()
        try:
            found = await self._model.run_structured(
                [
                    Message(role="system", content=prompts.classify(context)),
                    Message(role="user", content=last),
                ],
                Intents,
                max_tokens=256,
                thinking_budget=THINKING_BUDGET,
            )
        except AgentError:
            logger.warning("Classifying a message failed; every tool is offered")
            return frozenset(Intent)
        return frozenset(Intent(i) for i in found.intents)

    async def _second_look(
        self,
        last: str,
        tools: Sequence[ToolSpec],
        context: AssistantContext,
        check: CheckTool | None,
    ) -> tuple[str, list[ToolCall]]:
        """The user's last message alone, when a wish to write came back as words only.

        With a long history a small model may answer "it is recorded" instead of proposing a
        card. Read on its own, the request is told apart reliably: its cards are proposed
        with what the model says of them, or the first answer stands.
        """
        writes = [t for t in tools if t.writes]
        if not last or not writes:
            return "", []
        try:
            step = await self._model.run_structured(
                [
                    Message(role="system", content=prompts.system(writes, context, last)),
                    Message(role="user", content=last),
                ],
                Step,
                max_tokens=1024,
                thinking_budget=THINKING_BUDGET,
            )
        except AgentError:
            return "", []
        known = {t.name for t in writes}
        asked = [ToolCall(c.tool, c.arguments()) for c in step.calls if c.tool in known]
        return step.say, [c for c in asked if not (check and await check(c))]
