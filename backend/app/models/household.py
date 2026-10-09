"""Households: users keeping one budget together (E12, ADR-0017)."""

import enum
import secrets
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Model

if TYPE_CHECKING:
    from app.models.user import User


class HouseholdRole(enum.StrEnum):
    """What a member may do: the owner manages the household, a member may only leave."""

    OWNER = "owner"
    MEMBER = "member"


class Household(Model):
    """A group of users who keep one budget (F12.2).

    It reads its members' receipts and never owns them, so deleting it deletes nothing
    but the grouping. Its owner is the member whose role is `owner`.
    """

    __tablename__ = "households"

    name: Mapped[str] = mapped_column(String(60), nullable=False)
    # The secret in the household's invite link (F12.3); 128 random bits, so it cannot be
    # guessed, and replacing it is how the owner stops an old link working.
    invite_code: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        default=lambda: secrets.token_hex(16),
        server_default=text("replace((gen_random_uuid())::text, '-'::text, ''::text)"),
    )

    members: Mapped[list["HouseholdMember"]] = relationship(
        "HouseholdMember",
        back_populates="household",
        cascade="all, delete-orphan",
        order_by="HouseholdMember.created_at",
        lazy="selectin",
    )


class HouseholdMember(Model):
    """A user's place in a household; unique per user, so one household each (ADR-0017)."""

    __tablename__ = "household_members"

    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    role: Mapped[str] = mapped_column(String(10), nullable=False)

    household: Mapped[Household] = relationship(
        "Household", back_populates="members", lazy="joined"
    )
    user: Mapped["User"] = relationship("User", lazy="joined")
