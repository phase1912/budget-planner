"""What the user has now (F23.14)."""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.balance import Balance
from app.domain.income import regular_since
from app.domain.periods import DateRange
from app.models.income import Income
from app.models.user import User
from app.repository.income_source import IncomeSourceRepository
from app.repository.receipt import ReceiptRepository
from app.repository.regular_expense import RegularExpenseRepository
from app.repository.tax_payment import TaxPaymentRepository
from app.services.income import bill_rule, regular_rule, tax_rule
from app.services.money_accounts import AccountService, Overview


class BalanceService:
    """Carries the starting balance forward: income entered since and regular income as it
    arrived (F23.17), minus purchases since,
    minus taxes paid since — and, for a user who pays their own, what of it is still owed
    in taxes: set aside on taxed income since, plus the fixed sum each month (F23.16).

    Purchases count as the month does — read receipts, by their date, never a business
    trip's (counted_in_budget) — so the balance and Home's month never disagree.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def balance_of(self, user: User, today: date) -> Balance | None:
        """The balance on `today`, or None when the user has not entered a starting one.

        Once the user sees any account, the balance is the money on them all (F23.15):
        what reached and left them since each one opened, transfers between them
        cancelling out, and the starting balance no longer used.
        """
        accounts = await AccountService(self.session).overview(today)
        if accounts.accounts:
            return _from_accounts(accounts)
        if user.starting_balance is None or user.balance_since is None:
            return None
        since = min(user.balance_since, today)
        entered = await self.session.scalar(
            select(func.coalesce(func.sum(Income.amount), 0)).where(
                Income.user_id == user.id,
                Income.received_on >= since,
                Income.received_on <= today,
            )
        )
        regular = await IncomeSourceRepository(self.session).running_since(since)
        came_in = Decimal(entered or 0) + regular_since(
            (regular_rule(s) for s in regular), since, today
        )
        spent, _ = await ReceiptRepository(self.session).month_total(DateRange(since, today))
        paid = await TaxPaymentRepository(self.session).total(since, today)
        rule = tax_rule(user)
        owed = Decimal("0.00")
        if rule is not None:
            taxed = await self.session.scalar(
                select(func.coalesce(func.sum(Income.amount), 0)).where(
                    Income.user_id == user.id,
                    Income.taxed.is_(True),
                    Income.received_on >= since,
                    Income.received_on <= today,
                )
            )
            taxed_regular = regular_since(
                (regular_rule(s) for s in regular), since, today, taxed_only=True
            )
            months = (today.year - since.year) * 12 + today.month - since.month + 1
            owed = rule.on(Decimal(taxed or 0) + taxed_regular) + rule.fixed * months
        bills = regular_since(
            (
                bill_rule(b)
                for b in await RegularExpenseRepository(self.session).running_since(since)
            ),
            since,
            today,
        )
        return Balance(since, user.starting_balance, came_in, spent, paid, owed, bills)


def _from_accounts(overview: Overview) -> Balance:
    """The accounts' ledgers added up into one balance, from their earliest opening day.

    Money moved between two accounts the user sees cancels out; money from or to one they
    do not see (another member's own account) counts as having come in or gone.
    """
    ledgers = [a.ledger for a in overview.accounts]
    moved = sum((ledger.moved_in - ledger.moved_out for ledger in ledgers), Decimal("0.00"))
    return Balance(
        since=min(a.account.opening_on for a in overview.accounts),
        starting=sum((ledger.opening for ledger in ledgers), Decimal("0.00")),
        came_in=sum((ledger.came_in for ledger in ledgers), Decimal("0.00")) + moved,
        spent=sum((ledger.purchases for ledger in ledgers), Decimal("0.00")),
        taxes_paid=sum((ledger.taxes_paid for ledger in ledgers), Decimal("0.00")),
        taxes_owed=sum((ledger.taxes for ledger in ledgers), Decimal("0.00")),
        bills=sum((ledger.bills for ledger in ledgers), Decimal("0.00")),
        from_accounts=True,
    )
