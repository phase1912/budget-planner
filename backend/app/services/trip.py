import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import DomainError, NotFoundError, ProblemCode
from app.domain.periods import DateRange
from app.domain.trips import (
    ExpenseKind,
    TripKind,
    TripLine,
    TripSpending,
    TripSuggestion,
    kind_from_categories,
    split_spending,
    suggest_trips,
)
from app.models.receipt import Receipt, ReceiptStatus
from app.models.trip import Trip
from app.repository.receipt import ReceiptRepository
from app.repository.trip import TripRepository

SUGGESTION_LOOKBACK = timedelta(days=365)
"""How far back foreign receipts are looked at for an unrecorded trip."""


@dataclass(frozen=True)
class TripDetails:
    """What a trip is: the fields the user gives it."""

    kind: TripKind
    name: str
    country: str | None
    city: str | None
    start_date: date
    end_date: date
    purpose: str | None


@dataclass(frozen=True)
class TripSummary:
    """A trip with how many receipts it holds and what they come to.

    `asking_count`: receipts dated within a business trip, not yet said to be its own.
    """

    trip: Trip
    receipt_count: int
    total: Decimal
    asking_count: int = 0


class TripService:
    """The user's trips and which receipts are on them (F20.1)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.trips = TripRepository(session)

    async def list_trips(self, user_id: uuid.UUID) -> list[TripSummary]:
        """Every trip of the user's, latest first, with its read receipts' total."""
        return [await self._summary(trip) for trip in await self.trips.list_for(user_id)]

    async def get(
        self, user_id: uuid.UUID, trip_id: uuid.UUID
    ) -> tuple[TripSummary, Sequence[Receipt], Sequence[Receipt]]:
        """One trip, its receipts, and those a business trip still asks about (F20.1).

        Raises NotFoundError when it is not the user's (N2).
        """
        trip = await self._mine(user_id, trip_id)
        return (
            await self._summary(trip),
            await self.trips.receipts_of(trip),
            await self.trips.asking_about(trip),
        )

    async def _summary(self, trip: Trip) -> TripSummary:
        return TripSummary(
            trip, *await self.trips.totals(trip), await self.trips.asking_count(trip)
        )

    async def save(
        self, user_id: uuid.UUID, details: TripDetails, trip_id: uuid.UUID | None = None
    ) -> Trip:
        """Record a trip, or change one; its receipts follow its dates (F20.1).

        Raises NotFoundError for a trip that is not the user's (N2), and DomainError
        (`trips_overlap`) when its days meet another trip's: a receipt would belong to both.
        """
        clash = await self.trips.overlapping(user_id, details.start_date, details.end_date, trip_id)
        if clash is not None:
            raise DomainError(
                f"These dates meet the trip “{clash.name}” "
                f"({clash.start_date.isoformat()} to {clash.end_date.isoformat()}).",
                code=ProblemCode.TRIPS_OVERLAP,
                params={
                    "name": clash.name,
                    "start_on": clash.start_date.isoformat(),
                    "end_on": clash.end_date.isoformat(),
                },
            )
        trip = await self._mine(user_id, trip_id) if trip_id else Trip(user_id=user_id)
        trip.kind = details.kind
        trip.name = details.name.strip()
        trip.country = details.country.upper() if details.country else None
        trip.city = details.city.strip() if details.city else None
        trip.start_date = details.start_date
        trip.end_date = details.end_date
        trip.purpose = details.purpose.strip() if details.purpose else None
        self.session.add(trip)
        await self.session.flush()
        return trip

    async def delete(self, user_id: uuid.UUID, trip_id: uuid.UUID) -> None:
        """Forget a trip; receipts put in it by hand go back to their dates (N2 as above)."""
        trip = await self._mine(user_id, trip_id)
        await self.trips.release(trip)
        await self.session.delete(trip)
        await self.session.flush()

    async def place_receipt(
        self, receipt_id: uuid.UUID, trip_id: uuid.UUID | None, automatic: bool
    ) -> Receipt:
        """Put a receipt in a trip by hand, take it out of any, or give it back to its dates.

        A choice by hand is kept over the dates from then on. Raises NotFoundError for a
        receipt or trip that is not the current user's (N2).
        """
        receipts = ReceiptRepository(self.session)
        receipt = await receipts.get_with_items(receipt_id)
        if receipt is None:
            raise NotFoundError("Receipt not found")
        if automatic:
            receipt.trip_id, receipt.trip_manual = None, False
        else:
            if trip_id is not None:
                await self._mine(receipt.user_id, trip_id)
            receipt.trip_id, receipt.trip_manual = trip_id, True
        await self.session.flush()
        return receipt

    async def place_new(
        self, user_id: uuid.UUID, receipt: Receipt, trip_id: uuid.UUID | None
    ) -> None:
        """Put a receipt being stored in `trip_id`, or in no trip, as the user answered.

        The upload wizard asks whenever a receipt's date falls within a trip, and an upload
        started from a trip's page answers for it (F20.1). Raises NotFoundError for a trip
        that is not the user's (N2).
        """
        if trip_id is not None:
            await self._mine(user_id, trip_id)
        receipt.trip_id, receipt.trip_manual = trip_id, True

    async def choose_kind(self, receipt_id: uuid.UUID, kind: ExpenseKind | None) -> Receipt:
        """Set what a receipt paid for, or (None) give it back to the guess (F20.2).

        The choice outlives any later reading of the receipt. Raises NotFoundError for a
        receipt that is not the current user's (N2).
        """
        receipt = await ReceiptRepository(self.session).get_with_items(receipt_id)
        if receipt is None:
            raise NotFoundError("Receipt not found")
        receipt.expense_kind_chosen = kind
        await self.session.flush()
        return receipt

    async def suggestions(self, user_id: uuid.UUID) -> list[TripSuggestion]:
        """Runs of foreign receipts outside any trip that look like an unrecorded one."""
        since = datetime.now(UTC).date() - SUGGESTION_LOOKBACK
        return suggest_trips(await self.trips.foreign_days(user_id, since))

    async def in_month(self, user_id: uuid.UUID, month: DateRange) -> list[TripSummary]:
        """The trips with spending in `month`, and how much of it fell in that month."""
        found = []
        # Every trip is asked, not only those dated in the month: a receipt put in a trip by
        # hand may fall outside its dates.
        for trip in await self.trips.list_for(user_id):
            count, total = await self.trips.totals(trip, month)
            if count:
                found.append(TripSummary(trip, count, total))
        return found

    async def _mine(self, user_id: uuid.UUID, trip_id: uuid.UUID) -> Trip:
        trip = await self.trips.get(user_id, trip_id)
        if trip is None:
            raise NotFoundError("Trip not found")
        return trip


def kind_of(receipt: Receipt) -> ExpenseKind:
    """What a receipt paid for on a trip: the user's choice, else the model's guess (F20.2).

    A receipt read before kinds were guessed falls back to its lines' categories. Expects
    `line_items` and their categories loaded.
    """
    if receipt.expense_kind_chosen is not None:
        return receipt.expense_kind_chosen
    if receipt.expense_kind is not None:
        return receipt.expense_kind
    return kind_from_categories(
        [
            (item.category.name if item.category else None, item.total_price)
            for item in receipt.line_items
        ]
    )


def trip_spending(receipts: Sequence[Receipt], currency: str) -> TripSpending:
    """A trip's read receipts per kind in `currency`, the account's, and per currency paid.

    A converted receipt counts its printed total in the currency it was paid in; the rest
    were paid in the account's own. Receipts still in review count nowhere, as in the total.
    """
    lines = []
    for receipt in receipts:
        if receipt.status is not ReceiptStatus.PARSED:
            continue
        amount = sum((item.total_price for item in receipt.line_items), Decimal(0))
        paid_currency, paid_amount = currency, amount
        if receipt.original_currency and receipt.original_total is not None:
            paid_currency, paid_amount = receipt.original_currency, receipt.original_total
        lines.append(
            TripLine(
                kind=kind_of(receipt),
                amount=amount,
                paid_currency=paid_currency,
                paid_amount=paid_amount,
            )
        )
    return split_spending(lines)
