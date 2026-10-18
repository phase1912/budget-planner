"""Income read off a forwarded email, waiting for the user to confirm it (F23.11)."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Model


class PendingIncome(Model):
    """What a payslip or transfer confirmation sent by email says came in, not yet income.

    Kept apart from `Income` so it never counts in a month or the balance until the user
    confirms it, which turns it into an entry and removes this row; dismissing it only
    removes the row. The document itself is not kept. Any field the document did not
    show is null.
    """

    __tablename__ = "pending_incomes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    received_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    source: Mapped[str | None] = mapped_column(String(80), nullable=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="other")
    # The message it came in, so a letter delivered twice waits once.
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
