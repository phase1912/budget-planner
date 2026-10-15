import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import DomainError, NotFoundError, PerDiemError, ProblemCode
from app.domain.categories import UNCATEGORIZED
from app.domain.currency import ExchangeRate
from app.domain.per_diem import (
    Meal,
    PerDiemPart,
    PerDiemUnavailable,
    TripTimes,
    per_diem,
    rates_apply_from,
)
from app.domain.periods import DateRange
from app.domain.trips import (
    ExpenseKind,
    TripKind,
    TripLine,
    TripPurchase,
    TripSpending,
    TripStory,
    TripSuggestion,
    kind_from_categories,
    split_spending,
    suggest_trips,
    trip_story,
)
from app.models.receipt import Receipt, ReceiptStatus
from app.models.trip import Trip
from app.ports.exchange_rates import ExchangeRatePort, ExchangeRateUnavailable
from app.repository.exchange_rate import CachedExchangeRates
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
    budget: Decimal | None = None
    advance: Decimal | None = None
    advance_paid_on: date | None = None


@dataclass(frozen=True)
class TripSummary:
    """A trip with how many receipts it holds and what they come to.

    `asking_count`: receipts dated within a business trip, not yet said to be its own.
    """

    trip: Trip
    receipt_count: int
    total: Decimal
    asking_count: int = 0


@dataclass(frozen=True)
class PerDiem:
    """A business trip's per diem as worked out from its times, and what it is in złoty.

    `to_pln` holds the NBP rate used for each foreign currency, None where none could be
    had; `total_pln` is None unless every part could be put into złoty (ADR-0018).
    """

    times: TripTimes
    parts: list[PerDiemPart]
    to_pln: dict[str, ExchangeRate | None]
    total_pln: Decimal | None
    account_currency: str = "PLN"
    total_account: Decimal | None = None
    """The per diem in the account's currency, what the settlement adds up (F20.5)."""


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
        # Only a personal trip has a budget of its own; a business one is the employer's (F20.3).
        trip.budget = details.budget if details.kind is TripKind.PERSONAL else None
        # An advance is the employer's money paid ahead: a business trip's only (F20.5).
        business = details.kind is TripKind.BUSINESS
        trip.advance = details.advance if business else None
        trip.advance_paid_on = details.advance_paid_on if business and details.advance else None
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

    async def set_times(
        self, user_id: uuid.UUID, trip_id: uuid.UUID, times: TripTimes | None
    ) -> Trip:
        """Keep a business trip's times for its per diem, or (None) forget them (F20.4).

        Raises NotFoundError for a trip not the user's (N2), and PerDiemError for a
        personal trip, for times out of order, or for a trip before the rates kept.
        """
        trip = await self._mine(user_id, trip_id)
        if trip.kind is not TripKind.BUSINESS:
            raise PerDiemError(
                "A per diem is owed for a business trip only",
                code=ProblemCode.PER_DIEM_PERSONAL_TRIP,
            )
        if times is not None:
            try:
                per_diem(trip.country, times)
            except PerDiemUnavailable as error:
                raise _per_diem_error(error) from error
        trip.departed_at = times.departure if times else None
        trip.returned_at = times.returned if times else None
        trip.abroad_from = times.abroad_from if times else None
        trip.abroad_to = times.abroad_to if times else None
        trip.meals_provided = [list(day) for day in times.meals] if times else None
        await self.session.flush()
        return trip

    async def per_diem_of(
        self, trip: Trip, rates: ExchangeRatePort | None, account_currency: str = "PLN"
    ) -> PerDiem | None:
        """A business trip's per diem, itemised, in złoty and in the account's currency.

        None for a personal trip, one without times, or one whose times no longer give a
        per diem (F20.4). A foreign amount is converted at the NBP mid rate of the day the
        advance was paid (§ 20), or without an advance of the last working day before the
        return (ADR-0018); a missing rate leaves that total empty, never guessed.
        """
        times = times_of(trip)
        if trip.kind is not TripKind.BUSINESS or times is None:
            return None
        try:
            parts = per_diem(trip.country, times)
        except PerDiemUnavailable:
            return None
        rate_day = trip.advance_paid_on or times.returned.date() - timedelta(days=1)
        total_pln, to_pln = await self._total_in(parts, "PLN", rate_day, rates)
        total_account, _ = await self._total_in(parts, account_currency, rate_day, rates)
        return PerDiem(times, parts, to_pln, total_pln, account_currency, total_account)

    async def _total_in(
        self, parts: list[PerDiemPart], currency: str, day: date, rates: ExchangeRatePort | None
    ) -> tuple[Decimal | None, dict[str, ExchangeRate | None]]:
        """The parts added up in `currency`, and the rate each other currency took."""
        used: dict[str, ExchangeRate | None] = {}
        total: Decimal | None = Decimal("0.00")
        for part in parts:
            source = part.rate.currency
            if source == currency:
                total = None if total is None else total + part.total
                continue
            if source not in used:
                used[source] = None
                if rates is not None:
                    try:
                        used[source] = await CachedExchangeRates(rates, self.session).rate(
                            source, currency, day
                        )
                    except ExchangeRateUnavailable:
                        used[source] = None
            rate = used[source]
            total = (
                None
                if rate is None or total is None
                else total + (part.total * rate.rate).quantize(Decimal("0.01"))
            )
        return total, used

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


def story_of(trip: Trip, receipts: Sequence[Receipt]) -> TripStory:
    """What each day of a trip cost and where its money went, from its read lines (F20.3).

    Receipts still in review count nowhere, as in the trip's total. Expects `line_items`
    and their categories loaded.
    """
    purchases = [
        TripPurchase(
            day=(receipt.transaction_date or receipt.created_at).astimezone(UTC).date(),
            category=item.category.name if item.category else UNCATEGORIZED,
            amount=item.total_price,
        )
        for receipt in receipts
        if receipt.status is ReceiptStatus.PARSED
        for item in receipt.line_items
    ]
    return trip_story(trip.start_date, trip.end_date, purchases)


def times_of(trip: Trip) -> TripTimes | None:
    """A trip's stored times for its per diem, or None when the user gave none (F20.4)."""
    if trip.departed_at is None or trip.returned_at is None:
        return None
    return TripTimes(
        departure=trip.departed_at,
        returned=trip.returned_at,
        abroad_from=trip.abroad_from,
        abroad_to=trip.abroad_to,
        meals=tuple(tuple(Meal(m) for m in day) for day in trip.meals_provided or []),
    )


def _per_diem_error(error: PerDiemUnavailable) -> PerDiemError:
    if error.before_rates:
        return PerDiemError(
            str(error),
            code=ProblemCode.PER_DIEM_NO_RATES,
            params={"start_on": rates_apply_from().isoformat()},
        )
    return PerDiemError(str(error))
