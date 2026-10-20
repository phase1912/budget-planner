"""Money coming in (F23.10)."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Model


class Income(Model):
    """One sum that came in: a salary, a side job, a refund — on a day, from a source.

    A month's income is the sum of its entries; until the month has any, the account's
    usual income stands in. Entered by hand, or read from a payslip or a transfer
    confirmation (F23.11), whose file is not kept.
    """

    __tablename__ = "incomes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Shared with the user's household (F12.8): every member sees and changes it; None is
    # the author's own. Cleared when the author leaves, so it goes back to being theirs.
    household_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("households.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # The account it reached or leaves (F23.15); None: the author's purchase card, or
    # nowhere while they have no accounts.
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # The regular income whose month it confirms (F23.15): it stands in for the rule there.
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("income_sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Set aside on a business account when it came in, at the account's rate then.
    tax: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    received_on: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="salary")
    channel: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    # Taxes are set aside from it, for a user who pays their own (F23.16).
    taxed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
