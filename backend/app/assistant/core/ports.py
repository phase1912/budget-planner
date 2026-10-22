"""The assistant's core contract (F21.1, F21.7, ADR-0025, ADR-0028).

What the agent graph needs from the rest of the app — tools described, read and checked
by name — and what it gives back. Nothing here knows the database or HTTP: the app binds
the tools to a request, the graph only calls them.
"""

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


@dataclass(frozen=True)
class ToolSpec:
    """One thing the assistant may do: read something at once, or propose a write.

    `parameters` is the JSON schema of its arguments. A write tool never writes: the
    service turns its call into a card, saved only when the user approves it.
    """

    name: str
    description: str
    parameters: dict[str, Any]
    writes: bool


@dataclass(frozen=True)
class ToolCall:
    """The assistant asking for one tool, with its arguments."""

    name: str
    args: dict[str, Any]


@dataclass(frozen=True)
class Turn:
    """One message of the conversation as the assistant reads it back."""

    role: Literal["user", "assistant"]
    text: str


@dataclass(frozen=True)
class AssistantContext:
    """What the assistant must know about the user to answer: language, money, today."""

    language: str
    currency: str
    today: str
    categories: tuple[str, ...] = ()
    """The names of the categories the user's spending can go to (F21.3)."""
    max_rounds: int = 8
    """Rounds of tool use this user's message may take: fewer on the free plan, so one
    message cannot spend the month (F21.9.2)."""
    known: str = ""
    """What the user has, in a few lines — cards with their roles, bills, incomes, goals,
    trips, the family — so the model names things by their real names (F21.13.2)."""


@dataclass(frozen=True)
class AssistantReply:
    """What the assistant says back, the writes it proposes as cards, and — when it asks
    the user to choose — the options to tap (F21.13.3)."""

    text: str
    proposals: list[ToolCall] = field(default_factory=list)
    choices: list[str] = field(default_factory=list)


ReadTool = Callable[[ToolCall], Awaitable[str]]
"""Runs a read tool and returns its result, as text the assistant reads."""

CheckTool = Callable[[ToolCall], Awaitable[str | None]]
"""Why a write tool's arguments cannot become a card — a field that does not hold, a bill
named that the user has none of — or None when they can; the model is told so and gets
one more try, rather than the request being dropped in silence."""


class AssistantPort(Protocol):
    """Answers the user's latest message, using read tools as it needs them.

    Read tools run at once through `read`; write tools are only returned as proposals,
    each one `check` lets through. Never raises for a model failure: it answers that it
    could not, so the conversation goes on.
    """

    async def reply(
        self,
        history: Sequence[Turn],
        tools: Sequence[ToolSpec],
        read: ReadTool,
        context: AssistantContext,
        check: CheckTool | None = None,
    ) -> AssistantReply: ...
