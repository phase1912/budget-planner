"""Money coming in (F23.10)."""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import NotFoundError
from app.domain.income import IncomeChannel, MonthIncome, month_income
from app.domain.quota import next_month_start
from app.models.income import Income
from app.models.pending_income import PendingIncome
from app.models.user import User
from app.repository.income import IncomeRepository
from app.repository.pending_income import PendingIncomeRepository
from app.schemas.income import IncomeRequest


@dataclass(frozen=True)
class MonthIncomeView:
    month: date
    income: MonthIncome
    entries: list[Income]


class IncomeService:
    """An account's income entries and a month's total (F23.10)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.incomes = IncomeRepository(session)
        self.pending = PendingIncomeRepository(session)

    async def month(self, user: User, first_day: date) -> MonthIncomeView:
        """The entries of the month starting `first_day` and its income (usual if none)."""
        last_day = date.fromordinal(next_month_start(first_day).toordinal() - 1)
        entries = list(await self.incomes.between(first_day, last_day))
        return MonthIncomeView(
            first_day, month_income((e.amount for e in entries), user.usual_income), entries
        )

    async def total_for(self, user: User, first_day: date) -> Decimal | None:
        return (await self.month(user, first_day)).income.total

    async def add(self, request: IncomeRequest) -> Income:
        """Record a sum that came in, typed or confirmed from a document (`channel`)."""
        income = Income(**request.model_dump())
        self.incomes.add(income)
        await self.session.flush()
        return income

    async def update(self, income_id: uuid.UUID, request: IncomeRequest) -> Income:
        """Change an entry; NotFoundError for one not the user's (N2)."""
        income = await self.incomes.get(income_id)
        if income is None:
            raise NotFoundError("No such income.")
        # How an entry came in stays as it was: correcting it does not make it typed.
        for field, value in request.model_dump(exclude={"channel"}).items():
            setattr(income, field, value)
        await self.session.flush()
        return income

    async def delete(self, income_id: uuid.UUID) -> None:
        if not await self.incomes.delete(income_id):
            raise NotFoundError("No such income.")

    async def waiting(self) -> list[PendingIncome]:
        """Income read off forwarded documents, waiting to be confirmed (F23.11)."""
        return list(await self.pending.waiting())

    async def confirm(self, pending_id: uuid.UUID, request: IncomeRequest) -> Income:
        """Turn a pending income into an entry as the user confirmed or corrected it.

        It is kept as read from a document whatever `request.channel` says; the pending
        row goes. NotFoundError for one that is not the user's (N2).
        """
        pending = await self.pending.get(pending_id)
        if pending is None:
            raise NotFoundError("No such pending income.")
        income = await self.add(request.model_copy(update={"channel": IncomeChannel.DOCUMENT}))
        await self.session.delete(pending)
        await self.session.flush()
        return income

    async def dismiss(self, pending_id: uuid.UUID) -> None:
        """Drop a pending income without making it an entry; NotFoundError if not the user's."""
        if not await self.pending.delete(pending_id):
            raise NotFoundError("No such pending income.")
