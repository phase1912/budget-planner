"""Taxes a user paid themselves (F23.16)."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Model


class TaxPayment(Model):
    """A tax payment: money leaving the accounts that is not spending.

    It lowers the balance and what is still owed in taxes, and never shows among
    purchases, categories or the budget — a tax is not a thing bought.
    """

    __tablename__ = "tax_payments"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # The account it was paid from (F23.15); None: the author's purchase card, or
    # nowhere while they have no accounts.
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    paid_on: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
