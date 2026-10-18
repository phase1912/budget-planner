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
    received_on: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="salary")
    channel: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    # Taxes are set aside from it, for a user who pays their own (F23.16).
    taxed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
