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
        disable_reasoning: When True, every call asks the provider to skip its
            reasoning pass.  Set this for local hybrid-reasoning models (see
            ``Settings.llm_disable_reasoning``); hosted providers reject it.
        disable_json_schema: When True, ``run_structured`` stops sending
            ``response_format`` and relies on the prompt plus its own parsing.
            Set this for providers whose constrained decoding is broken (see
            ``Settings.llm_disable_json_schema``).
    """

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        api_base: str | None = None,
        default_temperature: float = 0.0,
        disable_reasoning: bool = False,
        disable_json_schema: bool = False,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.api_base = api_base
        self.default_temperature = default_temperature
        self.disable_reasoning = disable_reasoning
        self.disable_json_schema = disable_json_schema

    def _provider_kwargs(self) -> dict[str, Any]:
        """Build the credential and provider-tuning kwargs shared by both call paths.

        ``reasoning_effort`` travels inside ``extra_body`` rather than as a
        top-level argument because litellm swallows the top-level form for
        OpenAI-compatible providers and never puts it on the wire.
        """
        kwargs: dict[str, Any] = {}
        if self.api_key is not None:
            kwargs["api_key"] = self.api_key
        if self.api_base is not None:
            kwargs["api_base"] = self.api_base
        if self.disable_reasoning:
            kwargs["extra_body"] = {"reasoning_effort": "none"}
        return kwargs

    async def run(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int = 32768,
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
            "num_retries": 3,
        }
        kwargs.update(self._provider_kwargs())

        try:
            response = await litellm.acompletion(**kwargs)
        except Exception as exc:
            raise AgentError(f"LLM call failed: {exc}") from exc

        message = response.choices[0].message
        content = message.content
        if not content:
            raise AgentError(self._empty_content_reason(message, "LLM returned empty content"))
        return str(content)

    async def run_structured(
        self,
        messages: list[Message],
        schema: type[T],
        *,
        temperature: float | None = None,
        max_tokens: int = 32768,
    ) -> T:
        """Send messages and parse the response into a Pydantic model.

        Uses ``response_format`` with the JSON schema derived from the Pydantic
        model so providers that support structured output (Gemini, OpenAI, newer
        Claude) return valid JSON directly.  Falls back to extracting JSON from
        the text reply if the provider ignores ``response_format``. When
        ``disable_json_schema`` is set, the schema goes into the prompt instead:
        without either, a local model answers the question in prose.

        Raises ``AgentError`` if parsing fails after all attempts.
        """
        import litellm

        if self.disable_json_schema:
            messages = [*messages, self._json_only_instruction(schema)]
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature if temperature is not None else self.default_temperature,
            "max_tokens": max_tokens,
            "num_retries": 3,
        }
        if not self.disable_json_schema:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "strict": True,
                    "schema": schema.model_json_schema(),
                },
            }
        kwargs.update(self._provider_kwargs())

        try:
            response = await litellm.acompletion(**kwargs)
        except Exception as exc:
            raise AgentError(f"LLM call failed: {exc}") from exc

        message = response.choices[0].message
        raw = message.content
        if not raw:
            raise AgentError(
                self._empty_content_reason(
                    message, "LLM returned empty content for structured request"
                )
            )

        logger.debug("================ RAW LLM STRUCTURED RESPONSE ================")
        logger.debug(raw)
        logger.debug("=============================================================")

        return self._parse_response(str(raw), schema)

    @staticmethod
    def _json_only_instruction(schema: type[BaseModel]) -> Message:
        """Ask for bare JSON in words, for providers that cannot enforce a schema.

        Every adapter would otherwise have to remember to say it; the
        categoriser did not, and got markdown analysis back instead of JSON.
        """
        return Message(
            role="user",
            content=(
                "Respond with a single JSON object that conforms to this JSON Schema, "
                "and nothing else: no explanation, no markdown.\n"
                f"{json.dumps(schema.model_json_schema())}"
            ),
        )

    @staticmethod
    def _empty_content_reason(message: Any, base: str) -> str:
        """Explain an empty reply, naming the reasoning channel when it is the cause.

        Hybrid-reasoning models answer inside ``reasoning_content`` and leave
        ``content`` empty, which otherwise surfaces as a bare "empty content"
        error that says nothing about the fix.
        """
        reasoning = getattr(message, "reasoning_content", None)
        if not reasoning:
            return base
        return (
            f"{base}. The model answered in its reasoning channel instead "
            f"({len(str(reasoning))} chars). Set LLM_DISABLE_REASONING=true for this provider."
        )

    @staticmethod
    def _parse_response(raw: str, schema: type[T]) -> T:
        """Extract and validate JSON from the LLM's raw text output.

        Handles clean JSON, JSON wrapped in markdown code fences (```json ... ```)
        and JSON surrounded by a sentence of prose, all of which providers
        return even when asked for raw JSON.
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
            # Small models often wrap the object in a sentence even when told not
            # to; the outermost braces are the answer, the rest is chatter.
            start, end = text.find("{"), text.rfind("}")
            try:
                if start == -1 or end < start:
                    raise exc
                data = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                raise AgentError(
                    f"Failed to parse LLM response as JSON: {exc}\nRaw: {raw[:500]}"
                ) from exc

        try:
            return schema.model_validate(data)
        except Exception as exc:
            raise AgentError(f"LLM response did not match schema {schema.__name__}: {exc}") from exc
