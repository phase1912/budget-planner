"""Base protocol for agent tools.

A ``Tool`` is a capability the agent can invoke during a conversation.  Each
tool declares its name, description, and a JSON Schema for its parameters so
the LLM can choose to call it and provide the right arguments.

Implementations live in this package, one module per tool.  The agent receives
a list of ``Tool`` instances and serialises their schemas into the LLM's
``tools`` parameter automatically.
"""

from __future__ import annotations

from typing import Any, Protocol


class Tool(Protocol):
    """A callable capability exposed to the agent."""

    @property
    def name(self) -> str:
        """Unique identifier shown to the LLM (e.g. ``lookup_spending``)."""
        ...

    @property
    def description(self) -> str:
        """One-sentence purpose the LLM uses to decide when to call this tool."""
        ...

    @property
    def parameters_schema(self) -> dict[str, Any]:
        """JSON Schema describing the tool's keyword arguments."""
        ...

    async def execute(self, **kwargs: Any) -> str:
        """Run the tool with LLM-provided arguments and return a text result.

        The returned string is fed back to the LLM as a tool-result message.
        Raise ``ToolExecutionError`` for recoverable failures the LLM should
        know about.
        """
        ...


class ToolExecutionError(Exception):
    """Raised when a tool call fails in a way the LLM should see and handle."""
