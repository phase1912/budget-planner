"""Where each of the user's goals stands this month, whatever its kind (F8.11.2).

The Goals screen and the assistant read the same figures from here: a monthly cap's pace,
a savings goal's money against its target and date, a lifestyle goal's watched lines
against the months before. Only the caller's own receipts, goals and cards are read (N2).
"""

import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.categories import ItemView
from app.domain.goal_pace import PACED_KINDS, GoalPace, pace
from app.domain.goal_progress import LifestyleProgress, SavingsProgress
from app.domain.goals import FinancialKind, GoalType
from app.domain.periods import DateRange
from app.models.goal import Goal
from app.repository.goal import GoalRepository
from app.repository.receipt import ReceiptRepository
from app.services.money_accounts import AccountService

AVERAGED_MONTHS = 3
"""Whole months a lifestyle goal's month is measured against."""

Kind = Literal["month", "savings", "lifestyle"]


@dataclass(frozen=True)
class GoalStanding:
    """One goal and where it stands: exactly one of the three measures is set."""

    goal: Goal
    kind: Kind
    pace: GoalPace | None = None
    savings: SavingsProgress | None = None
    lifestyle: LifestyleProgress | None = None


async def month_pace(receipts: ReceiptRepository, goal: Goal, as_of: date) -> GoalPace | None:
    """Where a monthly money goal's month is heading, or None for any other goal (F6).

    Counts this month's spend up to `as_of` the way the month view does: parsed receipts
    only (D1, D3), on everything for a ceiling and on the one category for a cut.
    """
    if goal.financial_kind not in PACED_KINDS or goal.target_amount is None:
        return None
    month = DateRange(as_of.replace(day=1), as_of)
    if goal.financial_kind is FinancialKind.CATEGORY_REDUCTION:
        spent = (
            await receipts.item_spend(ItemView.ALL, period=month, category_id=goal.category_id)
        ).total
    else:
        spent, _ = await receipts.month_total(month)
    return pace(spent, goal.target_amount, as_of)


class GoalProgressService:
    """Every goal of the user's with where it stands on `today`."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.receipts = ReceiptRepository(session)

    async def standings(self, today: date) -> list[GoalStanding]:
        """The user's goals, newest first, each measured as its kind is."""
        balances = await self._balances(today)
        result = []
        for goal in await GoalRepository(self.session).list_mine():
            result.append(await self.standing(goal, today, balances))
        return result

    async def standing(
        self, goal: Goal, today: date, balances: dict[uuid.UUID, Decimal] | None = None
    ) -> GoalStanding:
        """Where one goal stands; `balances` spares reading the cards again for each."""
        if goal.type is GoalType.LIFESTYLE:
            return GoalStanding(goal, "lifestyle", lifestyle=await self._lifestyle(goal, today))
        if goal.financial_kind is FinancialKind.SAVINGS_TARGET:
            cards = balances if balances is not None else await self._balances(today)
            saved = cards.get(goal.saved_account_id) if goal.saved_account_id is not None else None
            if saved is None:
                saved = goal.saved_amount or Decimal(0)
            return GoalStanding(
                goal,
                "savings",
                savings=SavingsProgress(
                    saved, goal.target_amount or Decimal(0), goal.target_date, today
                ),
            )
        return GoalStanding(goal, "month", pace=await month_pace(self.receipts, goal, today))

    async def _lifestyle(self, goal: Goal, today: date) -> LifestyleProgress:
        """This month's spend on the watched lines against the average whole month of the
        three before it."""
        categories, keywords = tuple(goal.mapped_category_ids), tuple(goal.mapped_item_names)
        first = today.replace(day=1)
        this_month = await self.receipts.scope_spend(
            DateRange(first, today), category_ids=categories, keywords=keywords
        )
        index = first.year * 12 + first.month - 1 - AVERAGED_MONTHS
        before = DateRange(date(index // 12, index % 12 + 1, 1), first - timedelta(days=1))
        spent_before = await self.receipts.scope_spend(
            before, category_ids=categories, keywords=keywords
        )
        average = (spent_before / AVERAGED_MONTHS).quantize(Decimal("0.01"))
        return LifestyleProgress(this_month, average)

    async def _balances(self, today: date) -> dict[uuid.UUID, Decimal]:
        overview = await AccountService(self.session).overview(today)
        return {v.account.id: v.ledger.balance for v in overview.accounts}
