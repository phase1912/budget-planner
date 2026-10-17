"""What the user has now (F23.14)."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class Balance:
    """A balance carried forward from a starting amount by what came in and went out."""

    since: date
    starting: Decimal
    came_in: Decimal
    spent: Decimal

    @property
    def now(self) -> Decimal:
        """The starting amount, plus income since, minus counted purchases since."""
        return self.starting + self.came_in - self.spent
