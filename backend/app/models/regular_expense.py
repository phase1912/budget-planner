"""Spending that goes every month by itself (F23.18)."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Model


class RegularExpense(Model):
    """A bill paid every month — rent, a subscription, a loan — without a receipt.

    It runs from the month of `starts_on` until the month of `ends_on`, like a regular
    income: stopping one ends it, so past months keep what they cost. `day` is when in
    the month it goes, for the balance; None counts it on the 1st.
    """

    __tablename__ = "regular_expenses"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Shared with the user's household (F12.8): every member sees and changes it; None is
    # the author's own. Cleared when the author leaves, so it goes back to being theirs.
    household_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("households.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    day: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    # No longer read: a shared bill is never divided (ADR-0023). Dropped by a later
    # migration, once no running code maps it (ADR-0014).
    split: Mapped[str | None] = mapped_column(String(8), nullable=True)
