"""Provider-agnostic AI agent backed by litellm.

The ``Agent`` class is the single entry-point for every LLM call in the
application.  It delegates to litellm, which routes to the correct provider
based on the model string (e.g. ``gemini/gemini-2.0-flash``,
``anthropic/claude-sonnet-4-20250514``).

Two call patterns are supported:

1. **Unstructured** — ``agent.run(messages)`` returns the assistant's text.
2. **Structured** — ``agent.run_structured(messages, schema=MyModel)`` returns
   a validated Pydantic instance, using the provider's native JSON/tool-use
   mode where available.

Conversation history is the caller's responsibility: the Agent is stateless.
This keeps the extraction pipeline (one-shot) and the future goal-advice chat
(multi-turn) using the same class with no mode switch.
"""

from __future__ import annotations

import json
import logging
from typing import Any, TypeVar

from pydantic import BaseModel

from app.agent.types import Message

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class AgentError(Exception):
    """Raised when the LLM call fails or returns unparseable output."""


class Agent:
    """Stateless, provider-agnostic LLM caller.

    Wraps ``litellm.acompletion`` so every AI feature in the app speaks one
    interface regardless of whether the backend is Gemini, Claude or GPT.

    Args:
        model: A litellm model string, e.g. ``gemini/gemini-2.0-flash``.
        api_key: Provider API key.  When *None*, litellm falls back to
            provider-specific env vars (``GEMINI_API_KEY``, etc.).
        default_temperature: Sampling temperature used when the caller does
            not override it.
    """

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        default_temperature: float = 0.0,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.default_temperature = default_temperature

    async def run(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int = 4096,
    ) -> str:
        """Send messages to the LLM and return the assistant's text reply.

        This is the unstructured path — used when the caller wants free-form
        text (e.g. budget advice, goal insights).

        Raises ``AgentError`` if the provider returns an error or empty content.
        """
        import litellm

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature if temperature is not None else self.default_temperature,
            "max_tokens": max_tokens,
        }
        if self.api_key is not None:
            kwargs["api_key"] = self.api_key

        try:
            response = await litellm.acompletion(**kwargs)
        except Exception as exc:
            raise AgentError(f"LLM call failed: {exc}") from exc

        content = response.choices[0].message.content
        if not content:
            raise AgentError("LLM returned empty content")
        return str(content)

    async def run_structured(
        self,
        messages: list[Message],
        schema: type[T],
        *,
        temperature: float | None = None,
        max_tokens: int = 4096,
    ) -> T:
        """Send messages and parse the response into a Pydantic model.

        Uses ``response_format`` with the JSON schema derived from the Pydantic
        model so providers that support structured output (Gemini, OpenAI, newer
        Claude) return valid JSON directly.  Falls back to extracting JSON from
        the text reply if the provider ignores ``response_format``.

        Raises ``AgentError`` if parsing fails after all attempts.
        """
        import litellm

        json_schema = schema.model_json_schema()

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature if temperature is not None else self.default_temperature,
            "max_tokens": max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "strict": True,
                    "schema": json_schema,
                },
            },
        }
        if self.api_key is not None:
            kwargs["api_key"] = self.api_key

        try:
            response = await litellm.acompletion(**kwargs)
        except Exception as exc:
            raise AgentError(f"LLM call failed: {exc}") from exc

        raw = response.choices[0].message.content
        if not raw:
            raise AgentError("LLM returned empty content for structured request")

        return self._parse_response(str(raw), schema)

    @staticmethod
    def _parse_response(raw: str, schema: type[T]) -> T:
        """Extract and validate JSON from the LLM's raw text output.

        Handles both clean JSON responses and responses wrapped in markdown
        code fences (```json ... ```), which some providers add even when
        asked for raw JSON.
        """
        text = raw.strip()

        if text.startswith("```"):
            first_newline = text.index("\n") if "\n" in text else len(text)
            text = text[first_newline + 1 :]
            if text.endswith("```"):
                text = text[:-3].strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AgentError(
                f"Failed to parse LLM response as JSON: {exc}\nRaw: {raw[:500]}"
            ) from exc

        try:
            return schema.model_validate(data)
        except Exception as exc:
            raise AgentError(f"LLM response did not match schema {schema.__name__}: {exc}") from exc
