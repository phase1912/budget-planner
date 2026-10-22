"""The assistant at the API boundary (F21.1, F21.7)."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.assistant.tools.toolbox import card_form


class SendRequest(BaseModel):
    """What the user says or types; a new conversation when `conversation_id` is null.

    `upload_job_id` names the reading the files attached with the message started, through
    the same upload as the Add screen (F21.8.2), and `attached` how many receipts it reads.
    """

    text: str = Field(min_length=1, max_length=2000)
    conversation_id: uuid.UUID | None = None
    today: str | None = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    upload_job_id: uuid.UUID | None = None
    attached: int = Field(0, ge=0, le=50)


class SpeechRead(BaseModel):
    """What was said in a recording, for the user to send or correct (F21.2.2)."""

    text: str


class CardFields(BaseModel):
    """A card's fields as the user left them when approving it."""

    fields: dict[str, Any]
    today: str | None = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class CardRead(BaseModel):
    """A proposed action: what kind of thing it creates, changes or removes, and its fields
    — or an answer card (`answer`, F21.4): a chart and a link to the screen with the same
    filters; options to tap (`choice`, F21.13.3); files attached and being read
    (`attachment`, F21.8.2)."""

    kind: str
    """What the card does: `budget`, `income`, `bill`, `expense` and `answer` have cards of
    their own in the app; any other is drawn from `form` (F21.7.1)."""
    fields: dict[str, Any]
    form: list["FormFieldRead"] | None = None

    @model_validator(mode="after")
    def _drawn_from_its_tool(self) -> "CardRead":
        if self.form is None:
            drawn = card_form(self.kind)
            self.form = [FormFieldRead(**f) for f in drawn] if drawn else None
        return self


class FormFieldRead(BaseModel):
    """One field of a card drawn from its form: what it holds and how it is edited."""

    name: str
    kind: str
    options: list[str] = []
    required: bool = True


class MessageRead(BaseModel):
    """One message: text, or a card with its state and, once saved, what it created."""

    id: uuid.UUID
    role: Literal["user", "assistant"]
    text: str
    card: CardRead | None = None
    card_state: Literal["proposed", "saved", "dismissed", "shown"] | None = None
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
