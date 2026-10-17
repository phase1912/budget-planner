"""What the user has now (F23.14)."""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.balance import Balance
from app.domain.periods import DateRange
from app.models.income import Income
from app.models.user import User
from app.repository.receipt import ReceiptRepository


class BalanceService:
    """Carries the starting balance forward: income entered since, minus purchases since.

    Purchases count as the month does — read receipts, by their date, never a business
    trip's (counted_in_budget) — so the balance and Home's month never disagree.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def balance_of(self, user: User, today: date) -> Balance | None:
        """The balance on `today`, or None when the user has not entered a starting one."""
        if user.starting_balance is None or user.balance_since is None:
            return None
        since = min(user.balance_since, today)
        came_in = await self.session.scalar(
            select(func.coalesce(func.sum(Income.amount), 0)).where(
                Income.user_id == user.id,
                Income.received_on >= since,
                Income.received_on <= today,
            )
        )
        spent, _ = await ReceiptRepository(self.session).month_total(DateRange(since, today))
        return Balance(since, user.starting_balance, Decimal(came_in or 0), spent)
