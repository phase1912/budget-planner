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
    taxes_paid: Decimal = Decimal("0.00")
    taxes_owed: Decimal = Decimal("0.00")
    """For a user who pays their own taxes (F23.16): set aside on income since `since`."""
    bills: Decimal = Decimal("0.00")
    """Regular bills gone since `since` (F23.18) — spending without receipts."""

    @property
    def now(self) -> Decimal:
        """The starting amount, plus income since, minus counted purchases, regular bills
        and taxes paid."""
        return self.starting + self.came_in - self.spent - self.bills - self.taxes_paid

    @property
    def for_taxes(self) -> Decimal:
        """Of `now`, what is still owed in taxes: set aside but not yet paid, never below 0."""
        return max(self.taxes_owed - self.taxes_paid, Decimal("0.00"))
