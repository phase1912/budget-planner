"""Where a goal stands, whatever its kind (F8.11.2).

A monthly cap is measured by its pace (`app.domain.goal_pace`); a savings goal by what is
saved against its amount and, when it has a date, what is still needed a month to get
there; a lifestyle goal by what its watched lines cost this month against the months
before. Every figure is the user's own; nothing here guesses.
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

CENTS = Decimal("0.01")


def months_left(today: date, by: date) -> int:
    """The months a saving still has, this one counted: June 30 seen in October is 9,
    a date this month is 1, one already past is 0."""
    if by < today:
        return 0
    return (by.year - today.year) * 12 + by.month - today.month + 1


@dataclass(frozen=True)
class SavingsProgress:
    """A savings goal: `saved` of `target`, by `target_date` when it has one."""

    saved: Decimal
    target: Decimal
    target_date: date | None
    today: date

    @property
    def reached(self) -> bool:
        """Everything the goal asks for is saved."""
        return self.saved >= self.target

    @property
    def percent(self) -> int:
        """How much of the target is saved, 0 to 100."""
        if self.target <= 0:
            return 100
        share = self.saved / self.target * 100
        return int(max(Decimal(0), min(share, Decimal(100))).to_integral_value(ROUND_HALF_UP))

    @property
    def left(self) -> Decimal:
        """What is still to save, never below zero."""
        return max(self.target - self.saved, Decimal(0))

    @property
    def overdue(self) -> bool:
        """The date has passed and the money is not all there."""
        return self.target_date is not None and self.target_date < self.today and not self.reached

    @property
    def needed_per_month(self) -> Decimal | None:
        """What to put aside a month to reach the target by its date; None without a date,
        once reached, or once the date has passed."""
        if self.target_date is None or self.reached or self.overdue:
            return None
        months = months_left(self.today, self.target_date)
        return (self.left / months).quantize(CENTS, ROUND_HALF_UP)


@dataclass(frozen=True)
class LifestyleProgress:
    """A lifestyle goal: its watched lines this month against the months before."""

    this_month: Decimal
    monthly_average: Decimal

    @property
    def change_percent(self) -> int | None:
        """How this month compares, in percent; None with nothing before to compare."""
        if self.monthly_average <= 0:
            return None
        change = (self.this_month - self.monthly_average) / self.monthly_average * 100
        return int(change.to_integral_value(ROUND_HALF_UP))
