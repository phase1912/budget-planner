"""The per diem under Polish rules, case by case from the regulation's own paragraphs (F20.4).

The regulation (Dz.U. 2023 poz. 2190) gives no worked examples, so each case names the
provision it reads; the amounts follow from § 7 ust. 1 (45 zł) and the annex.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain.per_diem import (
    Meal,
    PerDiemUnavailable,
    TripTimes,
    per_diem,
    rate_for,
)


def _at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=UTC)


def _dues(country: str | None, times: TripTimes) -> list[tuple[str, list[str]]]:
    return [
        (part.rate.currency, [str(day.due) for day in part.days])
        for part in per_diem(country, times)
    ]


@pytest.mark.parametrize(
    ("hours", "due", "rule"),
    [
        (7, "0.00", "§ 7 ust. 3 pkt 1 lit. a"),
        (8, "22.50", "§ 7 ust. 3 pkt 1 lit. b"),
        (12, "22.50", "§ 7 ust. 3 pkt 1 lit. b"),
        (13, "45.00", "§ 7 ust. 3 pkt 1 lit. c"),
    ],
)
def test_a_domestic_trip_of_a_day_or_less_earns_by_its_hours(
    hours: int, due: str, rule: str
) -> None:
    """§ 7 ust. 3 pkt 1: under 8 hours nothing, 8 to 12 half, over 12 the whole 45 zł."""
    [part] = per_diem("PL", TripTimes(_at(13, 6), _at(13, 6 + hours)))

    assert ([str(d.due) for d in part.days], part.days[0].rule) == ([due], rule)


def test_a_longer_domestic_trip_earns_full_days_and_its_last_part_by_its_hours() -> None:
    """§ 7 ust. 3 pkt 2: 2 days and 6 hours is two full days and half a day."""
    assert _dues(None, TripTimes(_at(13, 6), _at(15, 12))) == [("PLN", ["45.00", "45.00", "22.50"])]
    assert _dues(None, TripTimes(_at(13, 6), _at(15, 15))) == [("PLN", ["45.00", "45.00", "45.00"])]


def test_meals_provided_at_home_take_their_share_of_the_rate() -> None:
    """§ 7 ust. 4: breakfast 25%, lunch 50%, dinner 25% of 45 zł."""
    times = TripTimes(_at(13, 6), _at(14, 20), meals=((Meal.BREAKFAST,), (Meal.LUNCH, Meal.DINNER)))

    [part] = per_diem("PL", times)

    assert [(str(d.reduction), str(d.due)) for d in part.days] == [
        ("11.25", "33.75"),
        ("33.75", "11.25"),
    ]
    assert part.days[0].meals_rule == "§ 7 ust. 4"


@pytest.mark.parametrize(
    ("hours", "due", "rule"),
    [
        (8, "16.33", "§ 13 ust. 3 pkt 2 lit. a"),
        (12, "24.50", "§ 13 ust. 3 pkt 2 lit. b"),
        (13, "49.00", "§ 13 ust. 3 pkt 2 lit. c"),
    ],
)
def test_part_of_a_day_abroad_earns_a_third_a_half_or_the_whole_rate(
    hours: int, due: str, rule: str
) -> None:
    """§ 13 ust. 3 pkt 2: up to 8 hours a third, over 8 to 12 half, over 12 all of 49 EUR."""
    [part] = per_diem("DE", TripTimes(_at(13, 6), _at(13, 6 + hours)))

    assert (part.rate.currency, str(part.days[0].due), part.days[0].rule) == ("EUR", due, rule)


def test_the_demo_trip_to_germany_with_two_hotel_breakfasts() -> None:
    """F20.4 demo: 13 Oct 06:00 to 15 Oct 21:00 is two days and 15 hours abroad, three
    full rates of 49 EUR, less 15% for each breakfast (§ 14 ust. 2): 132.30 EUR."""
    times = TripTimes(_at(13, 6), _at(15, 21), meals=((Meal.BREAKFAST,), (Meal.BREAKFAST,), ()))

    [part] = per_diem("DE", times)

    assert [(str(d.amount), str(d.reduction)) for d in part.days] == [
        ("49.00", "7.35"),
        ("49.00", "7.35"),
        ("49.00", "0.00"),
    ]
    assert (part.rate.currency, part.total) == ("EUR", Decimal("132.30"))


def test_hours_at_home_on_the_way_out_and_back_count_at_the_domestic_rate() -> None:
    """§ 21 with § 12: 6 hours to the border and 4 back, 10 hours at home, half of 45 zł."""
    times = TripTimes(
        departure=_at(13, 0),
        returned=_at(14, 20),
        abroad_from=_at(13, 6),
        abroad_to=_at(14, 16),
    )

    assert _dues("CZ", times) == [("EUR", ["41.00", "20.50"]), ("PLN", ["22.50"])]


def test_all_meals_abroad_leave_a_quarter_of_the_rate() -> None:
    """§ 14 ust. 1: full board abroad leaves 25% of the daily rate."""
    every_meal = (Meal.BREAKFAST, Meal.LUNCH, Meal.DINNER)
    [part] = per_diem("FR", TripTimes(_at(13, 0), _at(14, 0), meals=(every_meal,)))

    assert str(part.days[0].due) == "13.75"


def test_a_country_the_annex_does_not_list_takes_the_rate_for_other_countries() -> None:
    assert rate_for("NP", date(2026, 10, 1)).amount == Decimal(41)
    assert rate_for("GI", date(2026, 10, 1)).currency == "GBP"
    assert rate_for("US", date(2026, 10, 1)).amount == Decimal(59)


def test_times_out_of_order_or_before_the_rates_give_no_per_diem() -> None:
    with pytest.raises(PerDiemUnavailable):
        per_diem("PL", TripTimes(_at(14, 6), _at(13, 6)))
    with pytest.raises(PerDiemUnavailable):
        per_diem("DE", TripTimes(_at(13, 6), _at(14, 6), abroad_from=_at(14, 7)))
    with pytest.raises(PerDiemUnavailable):
        per_diem(
            "PL",
            TripTimes(datetime(2022, 6, 1, 6, tzinfo=UTC), datetime(2022, 6, 1, 20, tzinfo=UTC)),
        )
