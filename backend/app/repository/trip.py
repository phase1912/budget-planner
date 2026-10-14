import uuid
from collections.abc import Sequence
from datetime import UTC, date
from decimal import Decimal

from sqlalchemy import ColumnElement, and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.periods import DateRange
from app.domain.trips import ForeignDay
from app.models.line_item import LineItem
from app.models.receipt import Receipt, ReceiptStatus
from app.models.trip import Trip
from app.repository.receipt import _within, on_trip, purchase_day


def in_trip(trip: Trip) -> ColumnElement[bool]:
    """Receipts of `trip`: put in it by hand, or dated within it and not moved by hand."""
    return and_(
        Receipt.user_id == trip.user_id,
        or_(
            and_(Receipt.trip_manual, Receipt.trip_id == trip.id),
            and_(
                ~Receipt.trip_manual,
                purchase_day() >= trip.start_date,
                purchase_day() <= trip.end_date,
            ),
        ),
    )


class TripRepository:
    """The user's trips and their receipts (F20.1); every query names the user (N2)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for(self, user_id: uuid.UUID) -> Sequence[Trip]:
        """The user's trips, latest first."""
        stmt = select(Trip).where(Trip.user_id == user_id).order_by(Trip.start_date.desc())
        return (await self.session.execute(stmt)).scalars().all()

    async def get(self, user_id: uuid.UUID, trip_id: uuid.UUID) -> Trip | None:
        """One of the user's trips, or None — another user's is none (N2)."""
        stmt = select(Trip).where(Trip.id == trip_id, Trip.user_id == user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def overlapping(
        self, user_id: uuid.UUID, start: date, end: date, other_than: uuid.UUID | None
    ) -> Trip | None:
        """A trip of the user's sharing a day with `start` to `end`, other than `other_than`."""
        stmt = select(Trip).where(
            Trip.user_id == user_id, Trip.start_date <= end, Trip.end_date >= start
        )
        if other_than is not None:
            stmt = stmt.where(Trip.id != other_than)
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def totals(self, trip: Trip, period: DateRange | None = None) -> tuple[int, Decimal]:
        """How many read receipts a trip holds and what their lines add up to, in `period`."""
        receipts = select(Receipt.id).where(in_trip(trip), Receipt.status == ReceiptStatus.PARSED)
        if period is not None:
            receipts = receipts.where(_within(period))
        count = await self.session.scalar(select(func.count()).select_from(receipts.subquery()))
        total = await self.session.scalar(
            select(func.coalesce(func.sum(LineItem.total_price), 0)).where(
                LineItem.receipt_id.in_(receipts)
            )
        )
        return int(count or 0), Decimal(total or 0)

    async def receipts_of(self, trip: Trip) -> Sequence[Receipt]:
        """A trip's receipts of any status, oldest first."""
        stmt = (
            select(Receipt)
            .options(selectinload(Receipt.line_items))
            .where(in_trip(trip))
            .order_by(func.coalesce(Receipt.transaction_date, Receipt.created_at))
        )
        return (await self.session.execute(stmt)).scalars().unique().all()

    async def release(self, trip: Trip) -> None:
        """Hand the receipts put in `trip` by hand back to their dates, before it is deleted."""
        await self.session.execute(
            update(Receipt)
            .where(Receipt.trip_id == trip.id)
            .values(trip_id=None, trip_manual=False)
        )

    async def foreign_days(self, user_id: uuid.UUID, since: date) -> list[ForeignDay]:
        """The user's read foreign receipts outside any trip since `since`, per day and currency."""
        day = purchase_day()
        stmt = (
            select(
                day,
                Receipt.original_currency,
                func.count(func.distinct(Receipt.id)),
                func.coalesce(func.sum(LineItem.total_price), 0),
            )
            .outerjoin(LineItem, LineItem.receipt_id == Receipt.id)
            .where(
                Receipt.user_id == user_id,
                Receipt.status == ReceiptStatus.PARSED,
                Receipt.original_currency.is_not(None),
                ~on_trip(),
                day >= since,
            )
            .group_by(day, Receipt.original_currency)
        )
        return [
            ForeignDay(d, currency, int(count), Decimal(total))
            for d, currency, count, total in (await self.session.execute(stmt)).all()
        ]

    async def trip_of(self, receipt: Receipt) -> Trip | None:
        """The trip a receipt is on: the one put in by hand, else the one its date falls in."""
        if receipt.trip_manual:
            return await self.get(receipt.user_id, receipt.trip_id) if receipt.trip_id else None
        day = (receipt.transaction_date or receipt.created_at).astimezone(UTC).date()
        stmt = select(Trip).where(
            Trip.user_id == receipt.user_id, Trip.start_date <= day, Trip.end_date >= day
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()
