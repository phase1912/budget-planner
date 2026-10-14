"""Trips: which days look like one nobody recorded (F20.1)."""

from datetime import date
from decimal import Decimal

from app.domain.trips import ForeignDay, overlaps, suggest_trips


def _day(d: int, currency: str = "EUR", month: int = 10) -> ForeignDay:
    return ForeignDay(date(2026, month, d), currency, 1, Decimal("20.00"))


def test_foreign_receipts_on_days_in_a_row_suggest_a_trip() -> None:
    suggestions = suggest_trips([_day(3), _day(4), _day(6)])

    assert [(s.start, s.end, s.receipts, s.amount) for s in suggestions] == [
        (date(2026, 10, 3), date(2026, 10, 4), 2, Decimal("40.00"))
    ]


def test_one_day_abroad_or_another_currency_breaks_no_run_into_a_trip() -> None:
    assert suggest_trips([_day(3), _day(4, "USD")]) == []
    assert suggest_trips([_day(3)]) == []


def test_two_trips_overlap_when_they_share_a_day() -> None:
    assert overlaps(date(2026, 10, 1), date(2026, 10, 5), date(2026, 10, 5), date(2026, 10, 8))
    assert not overlaps(date(2026, 10, 1), date(2026, 10, 4), date(2026, 10, 5), date(2026, 10, 8))
