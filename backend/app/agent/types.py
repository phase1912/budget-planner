"""Internal type definitions for the agent package.

These types decouple the rest of the application from litellm's own types,
so the agent's public API stays stable even if the underlying library changes.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class ImageContent:
    """An image to include in a vision message.

    Accepts raw bytes and a MIME type; encodes to the base64 data-URL format
    that litellm (and the underlying providers) expect.
    """

    data: bytes
    media_type: str = "image/jpeg"

    def to_content_part(self) -> dict[str, Any]:
        """Serialize to the OpenAI-compatible image_url content block."""
        b64 = base64.b64encode(self.data).decode("ascii")
        return {
            "type": "image_url",
            "image_url": {"url": f"data:{self.media_type};base64,{b64}"},
        }


@dataclass
class Message:
    """A single message in a conversation.

    Uses the OpenAI message format (role + content) which litellm normalises
    across all providers.  For vision requests, ``content`` is a list of
    content blocks (text + images) rather than a plain string.
    """

    role: Literal["system", "user", "assistant", "tool"]
    content: str | list[dict[str, Any]]
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the dict format litellm expects."""
        msg: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name is not None:
            msg["name"] = self.name
        if self.tool_call_id is not None:
            msg["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls
        return msg
