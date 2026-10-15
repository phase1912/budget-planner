"""Trips: unrecorded ones found (F20.1), split by kind (F20.2), read as a story (F20.3)."""

import uuid
from datetime import date
from decimal import Decimal

from app.domain.trips import (
    ExpenseKind,
    ForeignDay,
    Placement,
    TripKind,
    TripLine,
    TripPurchase,
    TripSpan,
    budget_left,
    kind_from_categories,
    overlaps,
    parse_expense_kind,
    place,
    settle,
    split_spending,
    suggest_trips,
    trip_story,
)


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


def test_a_kind_named_by_the_model_is_read_and_anything_else_is_not() -> None:
    assert parse_expense_kind(" Transport ") is ExpenseKind.TRANSPORT
    assert parse_expense_kind("hotel") is None
    assert parse_expense_kind(None) is None


def test_a_receipt_read_before_kinds_takes_the_kind_holding_most_of_its_money() -> None:
    """F20.2: a supermarket run is meals; a souvenir shop with a drink on it is other."""
    groceries = [("Groceries", Decimal("40.00")), ("Other", Decimal("5.00"))]
    souvenirs = [("Other", Decimal("90.00")), ("Dining", Decimal("6.00"))]

    assert kind_from_categories(groceries) is ExpenseKind.MEALS
    assert kind_from_categories(souvenirs) is ExpenseKind.OTHER
    assert kind_from_categories([("Transport", Decimal("120.00"))]) is ExpenseKind.TRANSPORT
    assert kind_from_categories([]) is ExpenseKind.OTHER


def test_a_trip_splits_by_kind_with_every_kind_shown_and_by_currency_paid() -> None:
    """F20.2 demo: all-inclusive means accommodation 0.00, not a missing row."""
    spending = split_spending(
        [
            TripLine(ExpenseKind.TRANSPORT, Decimal("1900.00"), "PLN", Decimal("1900.00")),
            TripLine(ExpenseKind.MEALS, Decimal("310.00"), "PLN", Decimal("310.00")),
            TripLine(ExpenseKind.OTHER, Decimal("630.00"), "EGP", Decimal("7600.00")),
        ]
    )

    assert spending.by_kind == {
        ExpenseKind.TRANSPORT: Decimal("1900.00"),
        ExpenseKind.ACCOMMODATION: Decimal("0.00"),
        ExpenseKind.MEALS: Decimal("310.00"),
        ExpenseKind.OTHER: Decimal("630.00"),
    }
    assert spending.by_currency == {"PLN": Decimal("2210.00"), "EGP": Decimal("7600.00")}


EGYPT = TripSpan(uuid.uuid4(), TripKind.PERSONAL, date(2026, 10, 1), date(2026, 10, 8))
BERLIN = TripSpan(uuid.uuid4(), TripKind.BUSINESS, date(2026, 10, 13), date(2026, 10, 15))


def test_a_receipt_joins_a_personal_trip_by_date_but_a_business_trip_only_asks() -> None:
    """F20.1: an iPhone bought in Berlin is not the employer's until the user says so."""
    trips = [EGYPT, BERLIN]

    assert place(date(2026, 10, 3), False, None, trips) == Placement(EGYPT.id, None)
    assert place(date(2026, 10, 14), False, None, trips) == Placement(None, BERLIN.id)
    assert place(date(2026, 10, 20), False, None, trips) == Placement(None, None)


def test_a_receipt_placed_by_hand_stays_put_whatever_its_date() -> None:
    trips = [EGYPT, BERLIN]

    assert place(date(2026, 10, 14), True, BERLIN.id, trips) == Placement(BERLIN.id, None)
    assert place(date(2026, 10, 3), True, None, trips) == Placement(None, None)


def test_a_trip_story_shows_every_day_and_the_largest_category_first() -> None:
    """F20.3 demo: three days in the mountains, a quiet day still on the list."""
    story = trip_story(
        date(2026, 10, 10),
        date(2026, 10, 13),
        [
            TripPurchase(date(2026, 10, 10), "Accommodation", Decimal("900.00")),
            TripPurchase(date(2026, 10, 10), "Dining", Decimal("220.00")),
            TripPurchase(date(2026, 10, 12), "Dining", Decimal("640.00")),
            TripPurchase(date(2026, 10, 20), "Transport", Decimal("50.00")),  # put in by hand
        ],
    )

    assert story.days == [
        (date(2026, 10, 10), Decimal("1120.00")),
        (date(2026, 10, 11), Decimal("0.00")),
        (date(2026, 10, 12), Decimal("640.00")),
        (date(2026, 10, 13), Decimal("0.00")),
        (date(2026, 10, 20), Decimal("50.00")),
    ]
    assert story.categories == [
        ("Accommodation", Decimal("900.00")),
        ("Dining", Decimal("860.00")),
        ("Transport", Decimal("50.00")),
    ]


def test_what_is_left_of_a_budget_goes_below_zero_once_overspent() -> None:
    assert budget_left(Decimal("3000.00"), Decimal("2620.00")) == Decimal("380.00")
    assert budget_left(Decimal("3000.00"), Decimal("3100.00")) == Decimal("-100.00")
    assert budget_left(None, Decimal("10.00")) is None


def test_a_settlement_adds_expenses_and_per_diem_and_takes_the_advance_off() -> None:
    """F20.5 demo: 612.40 + 207.00 - 500.00 = 319.40."""
    sums = settle(Decimal("612.40"), True, Decimal("207.00"), Decimal("500.00"))

    assert sums.to_reimburse == Decimal("319.40")
    assert settle(Decimal("100.00"), False, None, Decimal("300.00")).to_reimburse == Decimal(
        "-200.00"
    )


def test_a_per_diem_claimed_but_not_converted_leaves_the_settlement_open() -> None:
    sums = settle(Decimal("612.40"), True, None, None)

    assert (sums.per_diem, sums.to_reimburse) == (None, None)
