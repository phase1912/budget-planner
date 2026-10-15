import uuid
from collections.abc import Sequence
from datetime import UTC, date
from decimal import Decimal

from sqlalchemy import ColumnElement, and_, false, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.periods import DateRange
from app.domain.trips import ForeignDay, TripKind, TripSpan, place
from app.models.line_item import LineItem
from app.models.receipt import Receipt, ReceiptStatus
from app.models.trip import Trip
from app.repository.receipt import _within, awaiting_answer, on_trip, purchase_day


def _dated_within(trip: Trip) -> ColumnElement[bool]:
    return and_(
        Receipt.user_id == trip.user_id,
        ~Receipt.trip_manual,
        purchase_day() >= trip.start_date,
        purchase_day() <= trip.end_date,
    )


def in_trip(trip: Trip) -> ColumnElement[bool]:
    """Receipts of `trip`: put in it by hand, or, for a personal trip, dated within it."""
    by_hand = and_(Receipt.user_id == trip.user_id, Receipt.trip_manual, Receipt.trip_id == trip.id)
    if trip.kind is TripKind.BUSINESS:
        return by_hand
    return or_(by_hand, _dated_within(trip))


def asked_by(trip: Trip) -> ColumnElement[bool]:
    """Receipts a business trip asks about: dated within it, nobody said either way yet."""
    if trip.kind is not TripKind.BUSINESS:
        return false()
    return _dated_within(trip)


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
        return await self._receipts(in_trip(trip))

    async def asking_about(self, trip: Trip) -> Sequence[Receipt]:
        """The receipts a business trip asks about, oldest first; none for a personal one."""
        return await self._receipts(asked_by(trip))

    async def _receipts(self, where: ColumnElement[bool]) -> Sequence[Receipt]:
        stmt = (
            select(Receipt)
            .options(selectinload(Receipt.line_items).selectinload(LineItem.category))
            .where(where)
            .order_by(func.coalesce(Receipt.transaction_date, Receipt.created_at))
        )
        return (await self.session.execute(stmt)).scalars().unique().all()

    async def asking_count(self, trip: Trip) -> int:
        """How many receipts a business trip still asks about."""
        count = await self.session.scalar(select(func.count(Receipt.id)).where(asked_by(trip)))
        return int(count or 0)

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
                ~awaiting_answer(),
                day >= since,
            )
            .group_by(day, Receipt.original_currency)
        )
        return [
            ForeignDay(d, currency, int(count), Decimal(total))
            for d, currency, count, total in (await self.session.execute(stmt)).all()
        ]

    async def placement(self, receipt: Receipt) -> tuple[Trip | None, Trip | None]:
        """The trip a receipt is on, and the business trip still asking about it (F20.1)."""
        return (await self.placements([receipt]))[receipt.id]

    async def placements(
        self, receipts: Sequence[Receipt]
    ) -> dict[uuid.UUID, tuple[Trip | None, Trip | None]]:
        """Each receipt's trip and asking business trip, its owner's trips read once each."""
        trips_of: dict[uuid.UUID, dict[uuid.UUID, Trip]] = {}
        placed = {}
        for receipt in receipts:
            if receipt.user_id not in trips_of:
                trips_of[receipt.user_id] = {t.id: t for t in await self.list_for(receipt.user_id)}
            trips = trips_of[receipt.user_id]
            spans = [TripSpan(t.id, t.kind, t.start_date, t.end_date) for t in trips.values()]
            day = (receipt.transaction_date or receipt.created_at).astimezone(UTC).date()
            spot = place(day, receipt.trip_manual, receipt.trip_id, spans)
            placed[receipt.id] = (
                trips.get(spot.trip_id) if spot.trip_id else None,
                trips.get(spot.asking_id) if spot.asking_id else None,
            )
        return placed
