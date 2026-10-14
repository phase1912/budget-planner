"""Trips: spending with a shape of its own, personal or on the employer's account (F20.1).

A receipt belongs to the trip whose dates hold its purchase day, unless the user moved it
in or out by hand. A personal trip stays in the user's month; a business trip is the
employer's money and stays out of it.
"""

import enum
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
