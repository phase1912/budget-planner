"""Trips: spending with a shape of its own, personal or on the employer's account (F20.1).

A receipt belongs to the personal trip whose dates hold its purchase day, unless the user
moved it in or out by hand. A business trip holds only what the user put in it: its dates
merely ask about the receipts within them, since a purchase on a business trip may be the
user's own. A personal trip stays in the user's month; a business trip is the employer's
money and stays out of it.
"""

import enum
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal


class TripKind(enum.StrEnum):
    """Whose money a trip is: the user's own, or the employer's to repay."""

    PERSONAL = "personal"
    BUSINESS = "business"


SUGGESTION_MIN_DAYS = 2
"""Foreign receipts on at least this many days in a row suggest a trip."""


@dataclass(frozen=True)
class ForeignDay:
    """One day's foreign receipts outside any trip: their count, currency and value."""

    day: date
    currency: str
    receipts: int
    amount: Decimal


@dataclass(frozen=True)
class TripSuggestion:
    """A run of days that looks like a trip nobody recorded (F20.1)."""

    start: date
    end: date
    currency: str
    receipts: int
    amount: Decimal


@dataclass(frozen=True)
class TripSpan:
    """What placing a receipt needs to know of a trip."""

    id: uuid.UUID
    kind: TripKind
    start_date: date
    end_date: date


@dataclass(frozen=True)
class Placement:
    """Which trip a receipt is on, and which business trip still asks about it (F20.1)."""

    trip_id: uuid.UUID | None
    asking_id: uuid.UUID | None


def place(
    day: date, by_hand: bool, chosen: uuid.UUID | None, trips: Sequence[TripSpan]
) -> Placement:
    """Place a receipt bought on `day` among the user's `trips` (F20.1).

    Moved by hand, it is on `chosen`, or on none. Otherwise it is on the personal trip
    whose dates hold `day`; a business trip whose dates hold it only asks, because a
    purchase on a business trip may be the user's own, and until answered it stays in
    the user's budget. The same rule as `on_trip()` and `awaiting_answer()` in SQL.
    """
    if by_hand:
        return Placement(chosen, None)
    within = next((t for t in trips if t.start_date <= day <= t.end_date), None)
    if within is None:
        return Placement(None, None)
    if within.kind is TripKind.BUSINESS:
        return Placement(None, within.id)
    return Placement(within.id, None)


def overlaps(a_start: date, a_end: date, b_start: date, b_end: date) -> bool:
    """Whether two runs of whole days, both ends included, share a day."""
    return a_start <= b_end and b_start <= a_end


def suggest_trips(days: list[ForeignDay]) -> list[TripSuggestion]:
    """Runs of foreign receipts on consecutive days, in one currency, as trip suggestions.

    A day apart breaks a run; so does another currency. Runs shorter than
    SUGGESTION_MIN_DAYS are an odd purchase abroad online, not a trip. Newest first.
    """
    runs: list[list[ForeignDay]] = []
    for day in sorted(days, key=lambda d: (d.currency, d.day)):
        last = runs[-1][-1] if runs else None
        if last and last.currency == day.currency and day.day - last.day <= timedelta(days=1):
            runs[-1].append(day)
        else:
            runs.append([day])
    suggestions = [
        TripSuggestion(
            start=run[0].day,
            end=run[-1].day,
            currency=run[0].currency,
            receipts=sum(d.receipts for d in run),
            amount=sum((d.amount for d in run), Decimal(0)),
        )
        for run in runs
        if (run[-1].day - run[0].day).days + 1 >= SUGGESTION_MIN_DAYS
    ]
    return sorted(suggestions, key=lambda s: s.start, reverse=True)


class ExpenseKind(enum.StrEnum):
    """What a trip's receipt paid for: the split a settlement asks for (F20.2)."""

    TRANSPORT = "transport"
    ACCOMMODATION = "accommodation"
    MEALS = "meals"
    OTHER = "other"


_KIND_OF_CATEGORY = {
    "transport": ExpenseKind.TRANSPORT,
    "dining": ExpenseKind.MEALS,
    "groceries": ExpenseKind.MEALS,
}


def parse_expense_kind(value: object) -> ExpenseKind | None:
    """The kind a model or a client named, or None for anything that is not one."""
    if not isinstance(value, str):
        return None
    try:
        return ExpenseKind(value.strip().lower())
    except ValueError:
        return None


def kind_from_categories(line_totals: Sequence[tuple[str | None, Decimal]]) -> ExpenseKind:
    """A receipt's kind from its lines' categories, for one read before kinds were (F20.2).

    The kind holding most of the money wins; a category with no kind of its own counts
    as other, so a shop that mostly sold souvenirs is other even with a drink on it.
    """
    weights: dict[ExpenseKind, Decimal] = {}
    for category, total in line_totals:
        kind = _KIND_OF_CATEGORY.get((category or "").lower(), ExpenseKind.OTHER)
        weights[kind] = weights.get(kind, Decimal(0)) + max(total, Decimal(0))
    if not weights:
        return ExpenseKind.OTHER
    return max(weights, key=lambda kind: (weights[kind], kind is not ExpenseKind.OTHER))


@dataclass(frozen=True)
class TripLine:
    """One read receipt of a trip, as its spending is split (F20.2)."""

    kind: ExpenseKind
    amount: Decimal
    """In the account's currency."""
    paid_currency: str
    paid_amount: Decimal
    """As printed, in the currency it was paid in."""


@dataclass(frozen=True)
class TripSpending:
    """A trip's spending per kind in the account's currency, and per currency paid."""

    by_kind: dict[ExpenseKind, Decimal]
    by_currency: dict[str, Decimal]


def split_spending(lines: list[TripLine]) -> TripSpending:
    """Add a trip's receipts up per kind, every kind present even at zero, and per currency.

    Zero kinds stay, because "accommodation 0.00" is an answer — the hotel was paid
    another way — that a missing row would not give. Currencies are only those paid in.
    """
    by_kind = dict.fromkeys(ExpenseKind, Decimal("0.00"))
    by_currency: dict[str, Decimal] = {}
    for line in lines:
        by_kind[line.kind] += line.amount
        by_currency[line.paid_currency] = (
            by_currency.get(line.paid_currency, Decimal(0)) + line.paid_amount
        )
    return TripSpending(by_kind, by_currency)


@dataclass(frozen=True)
class TripPurchase:
    """One line of a read receipt on a trip: the day it was bought, its category, its cost."""

    day: date
    category: str
    amount: Decimal


@dataclass(frozen=True)
class TripStory:
    """A trip read as one story (F20.3): what each day cost and where the money went."""

    days: list[tuple[date, Decimal]]
    """Every day of the trip, a day without spending at zero, oldest first; a receipt put
    in the trip by hand from outside its dates adds its own day."""
    categories: list[tuple[str, Decimal]]
    """Each category the trip's money went on, the largest first."""


def trip_story(start: date, end: date, purchases: Sequence[TripPurchase]) -> TripStory:
    """Add a trip's purchases up per day of the trip and per category (F20.3)."""
    by_day = {start + timedelta(days=n): Decimal("0.00") for n in range((end - start).days + 1)}
    by_category: dict[str, Decimal] = {}
    for purchase in purchases:
        by_day[purchase.day] = by_day.get(purchase.day, Decimal("0.00")) + purchase.amount
        by_category[purchase.category] = (
            by_category.get(purchase.category, Decimal("0.00")) + purchase.amount
        )
    return TripStory(
        days=sorted(by_day.items()),
        categories=sorted(by_category.items(), key=lambda pair: (-pair[1], pair[0])),
    )


def budget_left(budget: Decimal | None, spent: Decimal) -> Decimal | None:
    """What is left of a trip's budget, negative once it is overspent; None without one."""
    return None if budget is None else budget - spent


@dataclass(frozen=True)
class Settlement:
    """What the employer owes back for a business trip, in the account's currency (F20.5).

    `per_diem` is None when no per diem was claimed, and `to_reimburse` None when one was
    claimed but could not be put into the account's currency: a sum is never guessed.
    A negative `to_reimburse` is what the employee hands back of the advance.
    """

    expenses: Decimal
    per_diem: Decimal | None
    advance: Decimal
    to_reimburse: Decimal | None


def settle(
    expenses: Decimal, per_diem_claimed: bool, per_diem: Decimal | None, advance: Decimal | None
) -> Settlement:
    """Add a business trip up: its expenses and per diem, less the advance paid (F20.5)."""
    paid_ahead = advance or Decimal("0.00")
    owed = (
        None if per_diem_claimed and per_diem is None else expenses + (per_diem or 0) - paid_ahead
    )
    return Settlement(expenses, per_diem if per_diem_claimed else None, paid_ahead, owed)
