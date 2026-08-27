"""Universal, provider-agnostic AI agent package.

This package provides a thin wrapper around litellm that lets every AI-powered
feature in the system call any LLM provider (Anthropic, Google, OpenAI, etc.)
through a single interface. The model is selected by a configuration string,
so switching providers requires only changing an environment variable, not code.

Architecture: the Agent is a stateless callable. Conversation history (for
future dialog features like goal-optimization chat) is passed in as a list of
messages, not stored internally — the caller owns the memory.
"""

from app.agent.core import Agent
from app.agent.types import ImageContent, Message

__all__ = ["Agent", "ImageContent", "Message"]
