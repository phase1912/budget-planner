"""How a monthly money goal is tracking this month (BRD F6, F7 — F8.7, F8.8).

A goal that caps a month's spend — a spending ceiling, or a cut to one category —
is measured by where the month is heading: the spend so far, carried forward at the
same daily rate to the month's last day. On track means heading under the cap, and
then there is nothing to cut (F6); heading over it is what puts the goal at risk (F7).
"""

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.domain.goals import FinancialKind

PACED_KINDS = frozenset({FinancialKind.SPENDING_CEILING, FinancialKind.CATEGORY_REDUCTION})
"""The kinds of goal that cap a month's spend, and so have a pace to measure."""

CENTS = Decimal("0.01")


@dataclass(frozen=True)
class GoalPace:
    """One monthly goal's month so far and where it is heading.

    `spent` is this month's spend up to `as_of` on what the goal concerns;
    `projected` is that spend carried forward at the same daily rate to the
    month's end; `target` is the monthly cap. `day` of `days_in_month` says how
    much of the month the projection rests on.
    """

    spent: Decimal
    projected: Decimal
    target: Decimal
    day: int
    days_in_month: int

    @property
    def on_track(self) -> bool:
        """The month is heading to finish at or under the cap (F6)."""
        return self.projected <= self.target

    @property
    def margin(self) -> Decimal:
        """How far under the cap the month is heading; negative when over it."""
        return self.target - self.projected


def pace(spent: Decimal, target: Decimal, as_of: date) -> GoalPace:
    """Carry `spent`, the month's spend up to and including `as_of`, to the month's end.

    The daily rate is the spend so far over the days so far, `as_of` included, so
    on the last day the projection is the spend itself. Early in a month the rate
    rests on few days; `day` is there for anything that wants to say so.
    """
    days_in_month = calendar.monthrange(as_of.year, as_of.month)[1]
    projected = spent / as_of.day * days_in_month
    return GoalPace(
        spent=spent,
        projected=projected.quantize(CENTS, ROUND_HALF_UP),
        target=target,
        day=as_of.day,
        days_in_month=days_in_month,
    )
