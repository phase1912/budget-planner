"""The assistant the user talks to, behind a port (F21.1, ADR-0025)."""

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


@dataclass(frozen=True)
class AssistantReply:
    """What the assistant says back, and the writes it proposes as cards."""

    text: str
    proposals: list[ToolCall] = field(default_factory=list)


ReadTool = Callable[[ToolCall], Awaitable[str]]
"""Runs a read tool and returns its result, as text the assistant reads."""


class AssistantPort(Protocol):
    """Answers the user's latest message, using read tools as it needs them.

    Read tools run at once through `read`; write tools are only returned as proposals.
    Never raises for a model failure: it answers that it could not, so the conversation
    goes on.
    """

    async def reply(
        self,
        history: Sequence[Turn],
        tools: Sequence[ToolSpec],
        read: ReadTool,
        context: AssistantContext,
    ) -> AssistantReply: ...
