"""Checking a money goal against the user's recent months (F23.13)."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.budget import BudgetMonth
from app.domain.categories import ItemView
from app.domain.goal_check import GoalCheck, MonthlyCategory, check_goal_plan
from app.domain.goals import FinancialKind
from app.domain.periods import DateRange
from app.models.income import Income
from app.models.user import User
from app.repository.receipt import ReceiptRepository

MONTHS_BACK = 3


class GoalCheckService:
    """Gathers the last three whole months — spending by category and income — and lets
    `check_goal_plan` judge a goal against them. Only the caller's own data is read (N2).
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
        return check_goal_plan(
            kind,
            target,
            category_id=category_id,
            months=n,
            monthly_spend=spend / n if n else Decimal(0),
            categories=_averaged(categories, n),
            monthly_income=await self._monthly_income(user, counted),
        )

    async def _monthly_income(self, user: User, months: list[DateRange]) -> Decimal | None:
        """The usual income, else what was entered over the counted months, averaged."""
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
