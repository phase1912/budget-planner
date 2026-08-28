# ADR 0006: Use LiteLLM for Agent Provider Abstraction

**Date:** 2026-08-28
**Status:** Accepted

## Context

The budget agent must extract structured data from uploaded receipts, generating an `ExtractedReceipt` and a list of `ExtractedLineItem`s. While the default model requested for local/development use is `gemini-2.0-flash`, the product requirements demand provider flexibility. We need the ability to easily swap between different models and API providers (Anthropic, Google AI Studio, OpenAI, etc.) using the user's provided API keys, without rewriting the parsing integration each time.

Furthermore, we need to lay the foundation for more conversational, autonomous agent capabilities in the future (e.g. goal-based optimization and insights). 

## Decision

We have decided to use the `litellm` library as an abstraction layer for our LLM calls, wrapped inside our own `app.agent.Agent` class. 

## Consequences

**Positive:**
- **Provider Agnostic:** We can seamlessly switch between Gemini, Claude, and other models just by changing the `LLM_MODEL` setting string (e.g. `gemini/gemini-2.0-flash`).
- **Standardized Schema:** `litellm` normalizes structured output extraction across different providers, allowing us to just pass in a Pydantic schema.
- **Future Proof:** As the agent grows beyond basic data extraction and into conversation (managing a message history to help users optimize goals), the generic `Message` and `ImageContent` dataclasses we've defined will scale naturally with `litellm`.
- **Free to use:** `litellm` is an open-source (MIT licensed) standard package, avoiding "reinventing the wheel" for basic abstraction.

**Negative:**
- **Dependency:** Adds an external dependency to the project.
- **Leaky abstractions:** Occasionally, provider-specific features (like specific Vision processing parameters) might not be fully transparent through the abstraction layer and will require cautious handling.
