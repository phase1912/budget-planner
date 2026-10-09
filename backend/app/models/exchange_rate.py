from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Model


class CachedExchangeRate(Model):
    """A rate once fetched for a currency pair and purchase date (F11.7.2, ADR-0016).

    Shared by every user: a published rate is public and never changes, so a month of
    receipts costs a handful of calls to the rate source, and none once it is down.
    """

    __tablename__ = "exchange_rates"
    __table_args__ = (UniqueConstraint("base", "quote", "requested_date"),)

    base: Mapped[str] = mapped_column(String(3), nullable=False)
    quote: Mapped[str] = mapped_column(String(3), nullable=False)
    requested_date: Mapped[date] = mapped_column(Date, nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
