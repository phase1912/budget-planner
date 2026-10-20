"""Checking a money goal against the user's recent months (F23.13)."""

import uuid
from collections.abc import Sequence
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.budget import BudgetMonth
from app.domain.categories import ItemView
from app.domain.family_lines import swaps
from app.domain.goal_check import GoalCheck, MonthlyCategory, Verdict, check_goal_plan
from app.domain.goals import FinancialKind
from app.domain.periods import DateRange
from app.models.income import Income
from app.models.regular_expense import RegularExpense
from app.models.user import User
from app.repository.household import HouseholdRepository
from app.repository.household_spend import HouseholdSpendRepository
from app.repository.income_source import IncomeSourceRepository
from app.repository.receipt import ReceiptRepository
from app.repository.regular_expense import RegularExpenseRepository
from app.services.income import tax_rule

MONTHS_BACK = 3


class GoalCheckService:
    """Gathers the last three whole months — spending by category and income — and lets
    `check_goal_plan` judge a goal against them. Only the caller's own data is read (N2),
    except the product swaps of a stretch, which read the family's shared receipts (F12.11).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.receipts = ReceiptRepository(session)

    async def check(
        self,
        user: User,
        kind: FinancialKind,
        target: Decimal,
        category_id: uuid.UUID | None,
        today: date,
    ) -> GoalCheck:
        """The verdict for a goal not yet saved; months without receipts are not counted,
        so a new account is judged on what it has rather than on empty months."""
        months = [_month_before(today, n) for n in range(1, MONTHS_BACK + 1)]
        counted: list[DateRange] = []
        spend = Decimal(0)
        for month in months:
            total, receipts = await self.receipts.month_total(month)
            if receipts:
                counted.append(month)
                spend += total
        n = len(counted)
        categories: list[MonthlyCategory] = []
        for month in counted:
            for c in await self.receipts.spend_by_category(ItemView.ALL, period=month):
                categories.append(MonthlyCategory(c.category_id, c.name, c.total))
        result = check_goal_plan(
            kind,
            target,
            category_id=category_id,
            months=n,
            monthly_spend=spend / n if n else Decimal(0),
            categories=_averaged(categories, n),
            monthly_income=_less_bills(
                _after_taxes(user, await self._monthly_income(user, counted)),
                await RegularExpenseRepository(self.session).current(),
            ),
        )
        if result.verdict is not Verdict.STRETCH or not counted:
            return result
        return await self._with_swaps(user, result, counted, today)

    async def _with_swaps(
        self, user: User, result: GoalCheck, months: list[DateRange], today: date
    ) -> GoalCheck:
        """A stretch goal with the product swaps that close part of the gap (F12.11).

        In a family they come from every member's shared receipts and the family's own
        prices; alone, from the user's receipts.
        """
        household = await HouseholdRepository(self.session).membership_of(user.id)
        members = [m.user_id for m in household.household.members] if household else [user.id]
        period = DateRange(min(m.start for m in months), max(m.end for m in months))
        lines = await HouseholdSpendRepository(self.session).shared_lines(
            period, members, viewer_id=user.id
        )
        found = swaps(
            lines,
            Decimal(len(months)),
            today,
            timedelta(days=get_settings().price_freshness_days),
        )
        return replace(result, swaps=found, family=len(members) > 1)

    async def _monthly_income(self, user: User, months: list[DateRange]) -> Decimal | None:
        """The regular incomes (F23.17), else the usual income, else what was entered over
        the counted months, averaged."""
        regular = await IncomeSourceRepository(self.session).current()
        if regular:
            return sum((s.amount for s in regular), Decimal(0))
        if user.usual_income is not None:
            return user.usual_income
        if not months:
            return None
        entered = await self.session.scalar(
            select(func.sum(Income.amount)).where(
                Income.user_id == user.id,
                Income.received_on >= min(m.start for m in months),
                Income.received_on <= max(m.end for m in months),
            )
        )
        return None if entered is None else Decimal(entered) / len(months)


def _less_bills(income: Decimal | None, bills: Sequence[RegularExpense]) -> Decimal | None:
    """Income less the regular bills (F23.18): rent is not money a goal can take."""
    return None if income is None else income - sum((b.amount for b in bills), Decimal(0))


def _after_taxes(user: User, income: Decimal | None) -> Decimal | None:
    """What of a month's income is the user's to keep, for one who pays their own taxes:
    a savings goal comes out of that, not out of money owed to the tax office (F23.16)."""
    rule = tax_rule(user)
    if income is None or rule is None:
        return income
    return income - rule.on(income) - rule.fixed


def _month_before(today: date, n: int) -> DateRange:
    index = today.year * 12 + today.month - 1 - n
    return DateRange.of_month(BudgetMonth(index // 12, index % 12 + 1))


def _averaged(rows: list[MonthlyCategory], months: int) -> list[MonthlyCategory]:
    totals: dict[uuid.UUID | None, MonthlyCategory] = {}
    for row in rows:
        seen = totals.get(row.category_id)
        amount = row.monthly + (seen.monthly if seen else Decimal(0))
        totals[row.category_id] = MonthlyCategory(row.category_id, row.name, amount)
    return [MonthlyCategory(c.category_id, c.name, c.monthly / months) for c in totals.values()]
