"""The assistant at the API boundary (F21.1, F21.7)."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SendRequest(BaseModel):
    """What the user says or types; a new conversation when `conversation_id` is null."""

    text: str = Field(min_length=1, max_length=2000)
    conversation_id: uuid.UUID | None = None
    today: str | None = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class CardFields(BaseModel):
    """A card's fields as the user left them when approving it."""

    fields: dict[str, Any]
    today: str | None = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class CardRead(BaseModel):
    """A proposed action: what kind of thing it creates or changes, and its fields."""

    kind: Literal["budget", "income", "bill"]
    fields: dict[str, Any]


class MessageRead(BaseModel):
    """One message: text, or a card with its state and, once saved, what it created."""

    id: uuid.UUID
    role: Literal["user", "assistant"]
    text: str
    card: CardRead | None = None
    card_state: Literal["proposed", "saved", "dismissed"] | None = None
    saved_ref: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationSummary(BaseModel):
    """A conversation in the list: what it was about and when it was last touched."""

    id: uuid.UUID
    title: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationRead(ConversationSummary):
    """A conversation with its messages, oldest first."""

    messages: list[MessageRead]
