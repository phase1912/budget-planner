"""The household's month and statistics (F12.5, ADR-0017, BRD BR-4, BR-5)."""

import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.api.errors import NotFoundError, ProblemCode
from app.domain.budget import BudgetMonth, LimitUsage, MonthProgress, limit_usage
from app.domain.periods import DateRange
from app.models.household import Household
from app.models.user import User
from app.repository.household_spend import HouseholdSpendRepository, SharedCategorySpend
from app.services.household import HouseholdService


@dataclass(frozen=True)
class MemberShare:
    """One member's part of the household's spend: shared, and private as one sum (11h)."""

    user_id: uuid.UUID
    first_name: str
    shared_total: Decimal
    private_total: Decimal

    @property
    def total(self) -> Decimal:
        """Everything the member spent in the period, private included."""
        return self.shared_total + self.private_total


@dataclass(frozen=True)
class HouseholdMonth:
    """What a household spent in one month and how each member contributed (D1-D4, D7).

    Always computed live: a member who leaves takes their receipts, so a household's
    finished month is not frozen into a snapshot (ADR-0017).
    """

    month: BudgetMonth
    progress: MonthProgress
    total: Decimal
    receipt_count: int
    excluded_count: int
    excluded_amount: Decimal
    limit: LimitUsage | None
    members: list[MemberShare]


@dataclass(frozen=True)
class CategoryShare:
    """A category's part of the household's spend, as a percentage to one place."""

    spend: SharedCategorySpend
    share: Decimal


@dataclass(frozen=True)
class HouseholdStatistics:
    """A period's household spend by category over shared receipts, private as one row (E1)."""

    period: DateRange
    total: Decimal
    categories: list[CategoryShare]
    private_total: Decimal
    private_share: Decimal


@dataclass(frozen=True)
class MemberDay:
    """What one member spent on one day; zero on a day they bought nothing."""

    user_id: uuid.UUID
    total: Decimal


@dataclass(frozen=True)
class HouseholdDay:
    """One day of the period with each member's spending on it."""

    day: date
    members: list[MemberDay]


@dataclass(frozen=True)
class HouseholdDaily:
    """The household's spending day by day, per member (F12.5, F23.4).

    `undated_private` is the other members' private spending of the period: it counts in
    the household's totals, but has no day here, since a date would say too much (ADR-0017).
    """

    members: list[tuple[uuid.UUID, str]]
    days: list[HouseholdDay]
    undated_private: Decimal


class HouseholdBudgetService:
    """BR-4 and BR-5 over a household's members, for any one of them.

    Raises NotFoundError for a user in no household. Reads only sums: a private
    receipt contributes its money and nothing that would say what it was (11h).
    """

    def __init__(self, households: HouseholdService, spend: HouseholdSpendRepository) -> None:
        self.households = households
        self.spend = spend

    async def month(self, user: User, month: BudgetMonth, today: date) -> HouseholdMonth:
        """The household's month as of the user's `today`, against its budget (D4, D7)."""
        household = await self._household(user)
        members = {m.user_id: m.user.first_name for m in household.members}
        days = DateRange.of_month(month)
        by_member = await self.spend.by_member(days, list(members))
        excluded_count, excluded_amount = await self.spend.under_review(days, list(members))
        shares = sorted(
            (
                MemberShare(s.user_id, members[s.user_id], s.shared_total, s.private_total)
                for s in by_member
            ),
            key=lambda m: m.total,
            reverse=True,
        )
        total = sum((m.total for m in shares), Decimal(0))
        return HouseholdMonth(
            month=month,
            progress=month.progress(today),
            total=total,
            receipt_count=sum(s.shared_count + s.private_count for s in by_member),
            excluded_count=excluded_count,
            excluded_amount=excluded_amount,
            limit=limit_usage(total, household.budget_limit),
            members=shares,
        )

    async def statistics(self, user: User, period: DateRange) -> HouseholdStatistics:
        """Spend per category over the household's shared receipts, with private as one row."""
        household = await self._household(user)
        members = [m.user_id for m in household.members]
        categories = await self.spend.shared_categories(period, members)
        private_total = sum(
            (s.private_total for s in await self.spend.by_member(period, members)), Decimal(0)
        )
        total = sum((c.total for c in categories), private_total)
        return HouseholdStatistics(
            period=period,
            total=total,
            categories=[CategoryShare(c, _share(c.total, total)) for c in categories],
            private_total=private_total,
            private_share=_share(private_total, total),
        )

    async def daily(self, user: User, period: DateRange) -> HouseholdDaily:
        """Every day of `period` with each member's spending, the viewer's private included.

        Raises NotFoundError outside a household.
        """
        household = await self._household(user)
        members = [(m.user_id, m.user.first_name) for m in household.members]
        ids = [member for member, _ in members]
        totals = await self.spend.daily_by_member(period, ids, user.id)
        undated = sum(
            (
                s.private_total
                for s in await self.spend.by_member(period, ids)
                if s.user_id != user.id
            ),
            Decimal(0),
        )
        days = [
            HouseholdDay(
                spent_on,
                [MemberDay(member, totals.get((spent_on, member), Decimal(0))) for member in ids],
            )
            for spent_on in (period.start + timedelta(days=n) for n in range(period.days))
        ]
        return HouseholdDaily(members=members, days=days, undated_private=undated)

    async def _household(self, user: User) -> Household:
        household = await self.households.mine(user)
        if household is None:
            raise NotFoundError(
                "You do not belong to a household.", code=ProblemCode.NOT_IN_HOUSEHOLD
            )
        return household


def _share(part: Decimal, whole: Decimal) -> Decimal:
    if whole <= 0:
        return Decimal(0)
    return (part / whole * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
