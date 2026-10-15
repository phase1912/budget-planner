import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.trips import TripKind
from app.models.base import Model


class Trip(Model):
    """A trip the user recorded, personal or business, over whole days (F20.1).

    Its receipts are those whose purchase day falls from `start_date` to `end_date`, both
    included, unless moved in or out by hand (`Receipt.trip_manual`). One user's trips
    never overlap, so a receipt has at most one trip by its date.
    """

    __tablename__ = "trips"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[TripKind] = mapped_column(
        Enum(
            TripKind,
            name="trip_kind",
            native_enum=False,
            length=16,
            values_callable=lambda members: [m.value for m in members],
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    # What the user means to spend on a personal trip, in the account's currency (F20.3).
    budget: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    # A business trip's times as the user gives them, for its per diem (F20.4, ADR-0018):
    # when it left and came back, when it was abroad, and the meals provided each day.
    departed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    abroad_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    abroad_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    meals_provided: Mapped[list[list[str]] | None] = mapped_column(JSONB, nullable=True)
