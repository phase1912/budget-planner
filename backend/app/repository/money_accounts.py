"""Reading and writing accounts and the money between them (F23.15)."""

import uuid
from collections.abc import Collection, Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import current_user_id
from app.domain.periods import DateRange
from app.models.account import Account, AccountMove, RegularTransfer
from app.models.household import HouseholdMember
from app.models.income import Income
from app.models.income_source import IncomeSource
from app.models.line_item import LineItem
from app.models.receipt import Receipt
from app.models.regular_expense import RegularExpense
from app.models.tax_payment import TaxPayment
from app.repository.base import BaseRepository
from app.repository.receipt import _within, counted_in_budget, purchase_day
from app.repository.shared import SharedWithHousehold


def visible_accounts() -> Select[tuple[uuid.UUID]]:
    """The ids of the accounts the signed-in user sees: their own and their household's."""
    uid = current_user_id.get()
    households = select(HouseholdMember.household_id).where(HouseholdMember.user_id == uid)
    return select(Account.id).where(
        or_(Account.user_id == uid, Account.household_id.in_(households))
    )


class AccountRepository(SharedWithHousehold[Account]):
    """The signed-in user's accounts and the ones their household shares (N2, F12.8)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Account, session)

    async def visible(self) -> Sequence[Account]:
        """Every account the user sees, oldest first."""
        stmt = select(Account).order_by(Account.created_at)
        return (await self.session.execute(self._apply_ownership(stmt))).scalars().all()


class AccountMoveRepository(BaseRepository[AccountMove]):
    """Moves that touch an account the user sees, whoever made them (N2)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AccountMove, session)

    def _apply_ownership(self, stmt: Any) -> Any:
        if self._bypass_ownership_check:
            return stmt
        seen = visible_accounts()
        return stmt.where(
            or_(AccountMove.from_account_id.in_(seen), AccountMove.to_account_id.in_(seen))
        )

    async def until(self, today: date) -> Sequence[AccountMove]:
        """Every move up to `today`, oldest first."""
        stmt = (
            select(AccountMove)
            .where(AccountMove.moved_on <= today)
            .order_by(AccountMove.moved_on, AccountMove.created_at)
        )
        return (await self.session.execute(self._apply_ownership(stmt))).scalars().all()

    async def for_month(
        self, first_day: date, *, bill_id: uuid.UUID | None = None, rule_id: uuid.UUID | None = None
    ) -> AccountMove | None:
        """The change made to a rule's occurrence in the month starting `first_day`."""
        stmt = select(AccountMove).where(
            func.date_trunc("month", AccountMove.moved_on) == first_day,
            AccountMove.bill_id == bill_id if bill_id else AccountMove.rule_id == rule_id,
        )
        return (await self.session.execute(self._apply_ownership(stmt))).scalars().first()


class RegularTransferRepository(BaseRepository[RegularTransfer]):
    """Monthly transfers out of or into an account the user sees (N2)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(RegularTransfer, session)

    def _apply_ownership(self, stmt: Any) -> Any:
        if self._bypass_ownership_check:
            return stmt
        seen = visible_accounts()
        return stmt.where(
            or_(
                RegularTransfer.from_account_id.in_(seen),
                RegularTransfer.to_account_id.in_(seen),
            )
        )

    async def running(self) -> Sequence[RegularTransfer]:
        """Every monthly transfer, ended or not, oldest first: past months keep theirs."""
        stmt = select(RegularTransfer).order_by(RegularTransfer.created_at)
        return (await self.session.execute(self._apply_ownership(stmt))).scalars().all()


class AccountMoneyRepository:
    """What reached or left accounts, read across the household for the ledgers (F23.15).

    It reads other members' rows only as the ledger needs them — amounts on an account
    the caller sees — and the caller passes their own household's members.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def incomes(self, authors: Collection[uuid.UUID], until: date) -> Sequence[Income]:
        """The authors' income entries up to `until`."""
        stmt = select(Income).where(Income.user_id.in_(authors), Income.received_on <= until)
        return (await self.session.execute(stmt)).scalars().all()

    async def sources(self, authors: Collection[uuid.UUID]) -> Sequence[IncomeSource]:
        """The authors' regular incomes, ended or not."""
        stmt = select(IncomeSource).where(IncomeSource.user_id.in_(authors))
        return (await self.session.execute(stmt)).scalars().all()

    async def bills(self, authors: Collection[uuid.UUID]) -> Sequence[RegularExpense]:
        """The authors' regular bills, ended or not."""
        stmt = select(RegularExpense).where(RegularExpense.user_id.in_(authors))
        return (await self.session.execute(stmt)).scalars().all()

    async def tax_payments(
        self, authors: Collection[uuid.UUID], until: date
    ) -> Sequence[TaxPayment]:
        """The authors' tax payments up to `until`."""
        stmt = select(TaxPayment).where(
            TaxPayment.user_id.in_(authors), TaxPayment.paid_on <= until
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def purchases(
        self, buyers: Collection[uuid.UUID], period: DateRange
    ) -> list[tuple[uuid.UUID, date, bool, int, Decimal]]:
        """Each buyer's counted purchases by day: (buyer, day, private, receipts, paid).

        Counted as the month counts them (D1-D3), so an account and Home never disagree.
        """
        day = purchase_day()
        stmt = (
            select(
                Receipt.user_id,
                day,
                Receipt.is_private,
                func.count(func.distinct(Receipt.id)),
                func.coalesce(func.sum(LineItem.paid), 0),
            )
            .join(LineItem, LineItem.receipt_id == Receipt.id)
            .where(Receipt.user_id.in_(buyers), counted_in_budget(), _within(period))
            .group_by(Receipt.user_id, day, Receipt.is_private)
        )
        return [
            (user, d, private, int(count), Decimal(total))
            for user, d, private, count, total in (await self.session.execute(stmt)).all()
        ]
