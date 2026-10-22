"""The assistant as an agent graph (F21.1, F21.13, ADR-0025, ADR-0028, ADR-0032).

Two LangGraph nodes in a loop: `think` offers the model every tool as a function, in the
provider's own tool calling, and `use` runs what it asked for — a read answers at once, a
write is checked and kept as a proposed card, `ask_user` ends the turn with options to
tap — and hands each result back, until the model answers in words.
"""

import json
import logging
from collections.abc import Sequence
from typing import Any, Protocol, TypedDict

from app.agent.core import AgentError
from app.agent.metering import Purpose
from app.agent.types import Message, ToolTurn, ToolUse
from app.assistant.core import prompts
from app.assistant.core.language import worded
from app.assistant.core.ports import (
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

MAX_ROUNDS = 8
"""Rounds of tool use before the assistant must answer: a hard request needs three or four
— look, look again, propose — and a loop that goes on is cut off, not paid for."""
HISTORY = 20
"""The latest messages the assistant reads back; older ones are not needed to go on."""
THINKING_BUDGET = 1024
"""What Gemini may think before each round, added on top of the answer's limit: left
unbounded, its thoughts filled the limit and the answer came back empty."""
MAX_OPTIONS = 8

ASK_TOOL = {
    "type": "function",
    "function": {
        "name": prompts.ASK,
        "description": (
            "Ask the user to choose: when more than one thing fits what they said, or a "
            "detail you need is missing. The options are what they can tap — exact names "
            "from what they have, or short answers."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "One short question"},
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Two to eight options to tap",
                },
            },
            "required": ["question", "options"],
        },
    },
}


class ToolModel(Protocol):
    """The model the graph asks: messages and functions in, words and calls out (ADR-0032)."""

    async def run_tools(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]],
        *,
        max_tokens: int = ...,
        thinking_budget: int | None = ...,
        purpose: str = ...,
    ) -> ToolTurn: ...


class State(TypedDict, total=False):
    """What the graph carries from one round to the next."""

    messages: list[Message]
    pending: list[ToolUse]
    proposals: list[ToolCall]
    choices: list[str]
    said: str
    rounds: int
    done: bool


def function(spec: ToolSpec) -> dict[str, Any]:
    """A tool as the provider's function calling takes it."""
    kind = "Proposes a card the user approves." if spec.writes else "Reads, changes nothing."
    return {
        "type": "function",
        "function": {
            "name": spec.name,
            "description": f"{spec.description} {kind}",
            "parameters": spec.parameters,
        },
    }


class AssistantGraph(AssistantPort):
    """Answers through the model, which uses the tools as it sees fit until it is done."""

    def __init__(self, model: ToolModel) -> None:
        self._model = model

    async def reply(
        self,
        history: Sequence[Turn],
        tools: Sequence[ToolSpec],
        read: ReadTool,
        context: AssistantContext,
        check: CheckTool | None = None,
    ) -> AssistantReply:
        # Imported on the first message, not at start: every second of an instance's start
        # counts against Cloud Run's startup probe.
        from langgraph.graph import END, START, StateGraph

        specs = {t.name: t for t in tools}
        functions = [function(t) for t in tools] + [ASK_TOOL]
        # The language is the user's last message with words in it, not a bare number.
        spoken = worded([t.text for t in history if t.role == "user"])

        async def think(state: State) -> State:
            messages = state["messages"]
            try:
                turn = await self._model.run_tools(
                    messages,
                    functions,
                    max_tokens=2048,
                    thinking_budget=THINKING_BUDGET,
                    purpose=Purpose.ASSISTANT,
                )
            except AgentError:
                logger.exception("The assistant's model call failed")
                return {"done": True}
            said = turn.text.strip() or state.get("said", "")
            if not turn.calls:
                return {"said": said, "done": True}
            return {"messages": [*messages, turn.message], "said": said, "pending": turn.calls}

        async def use(state: State) -> State:
            calls = state.get("pending", [])
            messages = list(state["messages"])
            proposals = list(state.get("proposals", []))
            choices: list[str] = []
            said = state.get("said", "")
            for call in calls:
                result, asked, refused = await self._use(call, specs, read, check, proposals)
                if asked is not None:
                    said, choices = asked
                elif refused:
                    # Words written beside a refused call describe a card that will not be.
                    said = ""
                messages.append(
                    Message(role="tool", content=result, tool_call_id=call.id, name=call.name)
                )
            rounds = state.get("rounds", 0) + 1
            return {
                "messages": messages,
                "proposals": proposals,
                "choices": choices,
                "said": said,
                "rounds": rounds,
                "done": bool(choices) or rounds >= min(MAX_ROUNDS, context.max_rounds),
            }

        graph = StateGraph(State)
        graph.add_node("think", think)
        graph.add_node("use", use)
        graph.add_edge(START, "think")
        graph.add_conditional_edges("think", lambda s: END if s.get("done") else "use")
        graph.add_conditional_edges("use", lambda s: END if s.get("done") else "think")
        start: State = {
            "messages": [
                Message(role="system", content=prompts.system(context, spoken)),
                *(Message(role=t.role, content=t.text) for t in history[-HISTORY:]),
            ]
        }
        final: State = await graph.compile().ainvoke(start)  # type: ignore[assignment]
        return AssistantReply(
            final.get("said", ""),
            list(final.get("proposals", [])),
            list(final.get("choices", [])),
        )

    @staticmethod
    async def _use(
        call: ToolUse,
        specs: dict[str, ToolSpec],
        read: ReadTool,
        check: CheckTool | None,
        proposals: list[ToolCall],
    ) -> tuple[str, tuple[str, list[str]] | None, bool]:
        """Run one call: what to tell the model, the question and options if it asked, and
        whether a write was refused."""
        if call.name == prompts.ASK:
            options = [str(o).strip() for o in call.arguments.get("options", []) if str(o).strip()]
            question = str(call.arguments.get("question", "")).strip()
            if not options or not question:
                return "Ask with a question and at least one option.", None, False
            asked = (question, options[:MAX_OPTIONS])
            return "Shown to the user; wait for their answer.", asked, False
        spec = specs.get(call.name)
        if spec is None:
            return json.dumps({"error": f"there is no tool {call.name}"}), None, False
        wanted = ToolCall(call.name, call.arguments)
        if not spec.writes:
            return await read(wanted), None, False
        if check and (why := await check(wanted)):
            refusal = {"refused": why, "no card was made": True}
            return json.dumps(refusal, ensure_ascii=False), None, True
        proposals.append(wanted)
        return "Proposed to the user as a card; not saved until they approve it.", None, False
