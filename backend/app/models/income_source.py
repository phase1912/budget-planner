"""Income that comes every month by itself (F23.17)."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Model


class IncomeSource(Model):
    """A regular income — a salary, a side job, a pension — counted in every month it runs.

    What reaches the accounts; for one who pays their own taxes, `taxed` says whether
    their tax is still to come out of it. It runs from the month of `starts_on`
    until the month of `ends_on`; removing one ends it rather than deleting it, so past
    months keep the income they had. `day` is when in the month it arrives, for the
    balance; None counts it on the 1st.
    """

    __tablename__ = "income_sources"

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
    # "About" (F23.15): expected on its day until the user confirms what really came.
    about: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    day: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    # Weekly on this weekday (0 Monday … 6 Sunday) instead of monthly on `day` (F23.21).
    weekday: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    # For a user who pays their own taxes (F23.16): the tax is taken from it each month.
    taxed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
