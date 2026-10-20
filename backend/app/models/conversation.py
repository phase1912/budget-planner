"""Conversations with the assistant (F21.1, ADR-0025)."""

import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Model


class Conversation(Model):
    """One chat with the assistant, the user's own and kept until they delete it.

    Its title is the first thing the user asked, so the list says what each was about.
    Deleting the account deletes it with its messages (ON DELETE CASCADE), and the full
    export (F17.9) carries both, as any other personal data (ADR-0020).
    """

    __tablename__ = "conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)

    messages: Mapped[list["ConversationMessage"]] = relationship(
        "ConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.created_at",
        lazy="selectin",
    )


class ConversationMessage(Model):
    """One message: the user's text, the assistant's text, or a card the assistant proposed.

    A card is an action with its fields (`card`), proposed until the user saves or
    dismisses it (`card_state`); once saved, `saved_ref` names what it created. Nothing is
    written by the assistant itself: only saving a card does, through the screens'
    services (ADR-0025).
    """

    __tablename__ = "conversation_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    card: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    card_state: Mapped[str | None] = mapped_column(String(10), nullable=True)
    saved_ref: Mapped[str | None] = mapped_column(String(80), nullable=True)

    conversation: Mapped[Conversation] = relationship("Conversation", back_populates="messages")
