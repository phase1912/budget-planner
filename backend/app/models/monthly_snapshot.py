import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Model


class MonthlySnapshot(Model):
    """A completed month's figures, kept so a closed month stops changing (BRD D5).

    A cache of derived data, never the truth: it is written the first time a user
    looks at a month that has ended (ADR-0010) and deleted whenever a receipt in
    that month changes, to be rewritten from the receipts on the next look (D6).
    `created_at` is when this version of the month was finalised.
    """

    __tablename__ = "monthly_snapshots"
    __table_args__ = (
        UniqueConstraint("user_id", "year", "month", name="uq_monthly_snapshot_month"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    receipt_count: Mapped[int] = mapped_column(Integer, nullable=False)
    excluded_count: Mapped[int] = mapped_column(Integer, nullable=False)
    excluded_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
