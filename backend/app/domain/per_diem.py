"""The per diem an employer owes for a business trip under Polish rules (F20.4, ADR-0018).

The rules are those of the regulation on business travel of employees of public bodies
(Dz.U. 2023 poz. 2190, consolidated text), which also binds a private employer whose own
rules say nothing (Labour Code art. 77^5 § 5). Every amount here carries the provision it
follows, so the trip page can show how it was reached. Nothing is guessed: the times are
the user's, and a trip without them has no per diem.
"""

import enum
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from functools import cache
from pathlib import Path

DAY = timedelta(hours=24)
CENT = Decimal("0.01")
DOMESTIC = "PL"


class PerDiemUnavailable(Exception):
    """No per diem can be worked out: the times are wrong, or the trip is before the rates.

    `before_rates` tells the two apart: True when the trip starts before the rates in
    configuration apply (`rates_apply_from`), False when the times are out of order.
    """

    def __init__(self, message: str, *, before_rates: bool = False) -> None:
        super().__init__(message)
        self.before_rates = before_rates


class Meal(enum.StrEnum):
    """A meal provided free during the trip, which reduces the per diem (§ 7 ust. 4, § 14)."""

    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"


MEAL_SHARE = {
    False: {
        Meal.BREAKFAST: Decimal("0.25"),
        Meal.LUNCH: Decimal("0.50"),
        Meal.DINNER: Decimal("0.25"),
    },
    True: {
        Meal.BREAKFAST: Decimal("0.15"),
        Meal.LUNCH: Decimal("0.30"),
        Meal.DINNER: Decimal("0.30"),
    },
}
"""Each meal's share of the daily rate, at home (§ 7 ust. 4) and abroad (§ 14 ust. 2)."""


@dataclass(frozen=True)
class Rate:
    """The per diem for one day (doba) of travel, in the currency the regulation names."""

    currency: str
    amount: Decimal
    abroad: bool


@dataclass(frozen=True)
class PerDiemDay:
    """One day (doba, 24 hours from the start) of a trip, or the part day left at its end.

    `share` is the part of the daily rate the hours earn; `reduction` what the meals
    provided that day take off it, never more than it earned.
    """

    number: int
    hours: Decimal
    share: Decimal
    rule: str
    amount: Decimal
    meals: tuple[Meal, ...]
    reduction: Decimal
    meals_rule: str | None
    due: Decimal


@dataclass(frozen=True)
class PerDiemPart:
    """The per diem for the time abroad, or for the time at home, in its own currency."""

    abroad: bool
    country: str
    rate: Rate
    days: list[PerDiemDay]
    total: Decimal


@dataclass(frozen=True)
class TripTimes:
    """When a business trip left and came back, and when it was abroad, as the user says.

    `abroad_from` and `abroad_to` are when the border was crossed or the plane left the
    last Polish airport and landed back (§ 12); without them a trip abroad counts as
    abroad throughout. `meals` lists the meals provided on each day of the main part —
    abroad for a trip abroad, at home for one in Poland — the first day first.
    """

    departure: datetime
    returned: datetime
    abroad_from: datetime | None = None
    abroad_to: datetime | None = None
    meals: tuple[tuple[Meal, ...], ...] = ()


@cache
def _rates() -> dict[str, object]:
    path = Path(__file__).with_name("per_diem_rates_pl.json")
    data: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
    return data


def rates_apply_from() -> date:
    """The first day of a trip the rates in configuration can be used for."""
    return date.fromisoformat(str(_rates()["applies_from"]))


def rate_for(country: str | None, on: date) -> Rate:
    """The daily rate for a trip to `country` (ISO 3166-1 alpha-2) starting `on` (F20.4).

    Poland, or no country, is the domestic rate (§ 7 ust. 1); a country the annex does
    not list takes its rate for "other countries". Raises PerDiemUnavailable for a trip
    starting before the rates in configuration apply.
    """
    if on < rates_apply_from():
        raise PerDiemUnavailable(
            f"No per diem rates are kept for trips before {rates_apply_from()}",
            before_rates=True,
        )
    data = _rates()
    code = (country or DOMESTIC).upper()
    if code == DOMESTIC:
        entry = data["domestic"]
        abroad = False
    else:
        abroad_rates = data["abroad"]
        assert isinstance(abroad_rates, dict)
        entry = abroad_rates.get(code, data["elsewhere"])
        abroad = True
    assert isinstance(entry, dict)
    return Rate(str(entry["currency"]), Decimal(str(entry["amount"])), abroad)


def _hours(span: timedelta) -> Decimal:
    return (Decimal(span.total_seconds()) / Decimal(3600)).quantize(CENT)


def _shares(span: timedelta, abroad: bool) -> list[tuple[timedelta, Decimal, str]]:
    """How a stretch of travel splits into days and the share of the rate each earns."""
    if not abroad and span <= DAY:
        if span < timedelta(hours=8):
            return [(span, Decimal(0), "§ 7 ust. 3 pkt 1 lit. a")]
        if span <= timedelta(hours=12):
            return [(span, Decimal("0.5"), "§ 7 ust. 3 pkt 1 lit. b")]
        return [(span, Decimal(1), "§ 7 ust. 3 pkt 1 lit. c")]
    full, rest = divmod(span, DAY)
    days = [(DAY, Decimal(1), "§ 13 ust. 3 pkt 1" if abroad else "§ 7 ust. 3 pkt 2")] * full
    if rest:
        if abroad:
            if rest <= timedelta(hours=8):
                days.append((rest, Decimal(1) / 3, "§ 13 ust. 3 pkt 2 lit. a"))
            elif rest <= timedelta(hours=12):
                days.append((rest, Decimal("0.5"), "§ 13 ust. 3 pkt 2 lit. b"))
            else:
                days.append((rest, Decimal(1), "§ 13 ust. 3 pkt 2 lit. c"))
        elif rest <= timedelta(hours=8):
            days.append((rest, Decimal("0.5"), "§ 7 ust. 3 pkt 2 lit. a"))
        else:
            days.append((rest, Decimal(1), "§ 7 ust. 3 pkt 2 lit. b"))
    return days


def _part(
    span: timedelta, country: str, rate: Rate, meals: tuple[tuple[Meal, ...], ...]
) -> PerDiemPart:
    days = []
    for number, (length, share, rule) in enumerate(_shares(span, rate.abroad), start=1):
        amount = (rate.amount * share).quantize(CENT, ROUND_HALF_UP)
        provided = meals[number - 1] if number <= len(meals) else ()
        taken = sum((MEAL_SHARE[rate.abroad][m] for m in set(provided)), Decimal(0))
        reduction = min((rate.amount * taken).quantize(CENT, ROUND_HALF_UP), amount)
        days.append(
            PerDiemDay(
                number=number,
                hours=_hours(length),
                share=share,
                rule=rule,
                amount=amount,
                meals=tuple(sorted(set(provided))),
                reduction=reduction,
                meals_rule=("§ 14 ust. 2" if rate.abroad else "§ 7 ust. 4") if provided else None,
                due=amount - reduction,
            )
        )
    return PerDiemPart(
        abroad=rate.abroad,
        country=country,
        rate=rate,
        days=days,
        total=sum((d.due for d in days), Decimal("0.00")),
    )


def per_diem(country: str | None, times: TripTimes) -> list[PerDiemPart]:
    """The per diem for a business trip, itemised by day, abroad and at home (F20.4).

    A trip in Poland is one domestic part (§ 7). A trip abroad is the time abroad at the
    destination's rate (§ 12, § 13), meals off it (§ 14), plus, when the user gave the
    border times, the hours at home on the way out and back together at the domestic
    rate (§ 21). Raises PerDiemUnavailable for times out of order or before the rates.
    """
    rate = rate_for(country, times.departure.date())
    if times.returned <= times.departure:
        raise PerDiemUnavailable("A trip returns after it leaves")
    if not rate.abroad:
        return [_part(times.returned - times.departure, DOMESTIC, rate, times.meals)]
    abroad_from = times.abroad_from or times.departure
    abroad_to = times.abroad_to or times.returned
    if not times.departure <= abroad_from < abroad_to <= times.returned:
        raise PerDiemUnavailable("The time abroad falls within the trip, and ends after it starts")
    code = (country or DOMESTIC).upper()
    parts = [_part(abroad_to - abroad_from, code, rate, times.meals)]
    at_home = (abroad_from - times.departure) + (times.returned - abroad_to)
    if at_home > timedelta(0):
        domestic = rate_for(DOMESTIC, times.departure.date())
        parts.append(_part(at_home, DOMESTIC, domestic, ()))
    return parts
