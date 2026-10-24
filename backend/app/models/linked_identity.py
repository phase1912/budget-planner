"""Accounts at Google or Apple that sign in to a user's account (F1.6, ADR-0035)."""

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Model


class LinkedIdentity(Model):
    """One provider account (its stable `subject`) that signs in as `user_id` (F1.6.1).

    A provider account belongs to one user only, and a user has at most one of each
    provider. `email` is what the provider said when linked — Apple's private relay
    address kept as given. `refresh_token` is Apple's, encrypted, kept only so deleting
    the account can revoke it (F1.6.3); Google's tokens are never kept.
    """

    __tablename__ = "linked_identities"
    __table_args__ = (
        UniqueConstraint("provider", "subject", name="uq_linked_identities_provider_subject"),
        UniqueConstraint("user_id", "provider", name="uq_linked_identities_user_provider"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(16), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Which of our client ids the token was issued to: Apple revokes only with that one.
    client_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
