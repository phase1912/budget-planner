"""Accounts and the money moved between them (F23.15, ADR-0024)."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Model


class Account(Model):
    """Where some of the money is: a card, a business account, a deposit.

    Its author's own, or shared with their household (`household_id`, as F12.8's money).
    It holds `opening` on `opening_on` and moves from there with what reaches or leaves it.
    `for_purchases` marks the card receipts are paid from: a personal one for its author,
    a shared one for every member who has no personal one marked. A business account
    sets `tax_rate` aside of each payment from outside; a deposit is just its amount.
    """

    __tablename__ = "accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    household_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("households.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    opening: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    opening_on: Mapped[date] = mapped_column(Date, nullable=False)
    tax_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    for_purchases: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )


class AccountMove(Model):
    """Money between accounts, or out of or into one, that is not income from outside.

    A transfer has both accounts and is neither income nor spending; a bill has only the
    account it left; an adjustment has the one it corrects, `to` raising it and `from`
    lowering it. One made for a rule's month (`bill_id` or `rule_id`) is that month's
    occurrence as the user changed it, standing in for the rule there; 0 skips it.
    """

    __tablename__ = "account_moves"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    moved_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    from_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=True, index=True
    )
    to_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=True, index=True
    )
    bill_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("regular_expenses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("regular_transfers.id", ondelete="SET NULL"), nullable=True, index=True
    )


class RegularTransfer(Model):
    """Money moved between two accounts every month by itself — what a family pays itself.

    It runs from the month of `starts_on` until the month of `ends_on`, as a regular
    income does, and never starts on a day already past (F23.15).
    """

    __tablename__ = "regular_transfers"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    day: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    from_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    to_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
