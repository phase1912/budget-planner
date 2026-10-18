"""Money coming in (F23.10)."""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import NotFoundError
from app.domain.income import (
    IncomeChannel,
    MonthIncome,
    Recurring,
    TaxRule,
    month_income,
    taxed_by_default,
)
from app.domain.quota import next_month_start
from app.models.income import Income
from app.models.income_source import IncomeSource
from app.models.pending_income import PendingIncome
from app.models.regular_expense import RegularExpense
from app.models.tax_payment import TaxPayment
from app.models.user import User
from app.repository.income import IncomeRepository
from app.repository.income_source import IncomeSourceRepository
from app.repository.pending_income import PendingIncomeRepository
from app.repository.regular_expense import RegularExpenseRepository
from app.repository.tax_payment import TaxPaymentRepository
from app.schemas.income import (
    IncomeRequest,
    IncomeSourceRequest,
    RegularExpenseRequest,
    TaxPaymentRequest,
)


def regular_rule(source: IncomeSource) -> Recurring:
    """A regular income as the domain rules read it."""
    return Recurring(source.amount, source.day, source.starts_on, source.ends_on, source.taxed)


def bill_rule(bill: RegularExpense) -> Recurring:
    """A regular bill as the domain rules read it."""
    return Recurring(bill.amount, bill.day, bill.starts_on, bill.ends_on)


def tax_rule(user: User) -> TaxRule | None:
    """What the user sets aside for taxes, or None when they do not pay their own (F23.16)."""
    if not user.pays_own_taxes:
        return None
    return TaxRule(user.tax_rate or Decimal(0), user.tax_fixed_monthly or Decimal(0))


@dataclass(frozen=True)
class MonthIncomeView:
    month: date
    income: MonthIncome
    entries: list[Income]
    taxes_paid: Decimal
    regular: list[IncomeSource]
    bills: list[RegularExpense]


class IncomeService:
    """An account's income entries and a month's total (F23.10)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.incomes = IncomeRepository(session)
        self.pending = PendingIncomeRepository(session)
        self.tax_payments = TaxPaymentRepository(session)
        self.sources = IncomeSourceRepository(session)
        self.bills = RegularExpenseRepository(session)

    async def month(self, user: User, first_day: date) -> MonthIncomeView:
        """The entries of the month starting `first_day` and its income (usual if none)."""
        last_day = date.fromordinal(next_month_start(first_day).toordinal() - 1)
        entries = list(await self.incomes.between(first_day, last_day))
        regular = [
            s
            for s in await self.sources.running_since(first_day)
            if regular_rule(s).runs_in(first_day)
        ]
        income = month_income(
            ((e.amount, e.taxed) for e in entries),
            user.usual_income,
            tax_rule(user),
            recurring=((s.amount, s.taxed) for s in regular),
        )
        paid = await self.tax_payments.total(first_day, last_day)
        bills = [
            b for b in await self.bills.running_since(first_day) if bill_rule(b).runs_in(first_day)
        ]
        return MonthIncomeView(first_day, income, entries, paid, regular, bills)

    async def regular_bills(self) -> list[RegularExpense]:
        """The regular bills still running (F23.18)."""
        return list(await self.bills.current())

    async def add_bill(self, request: RegularExpenseRequest, today: date) -> RegularExpense:
        """Start a regular bill: it counts from this month on."""
        bill = RegularExpense(**request.model_dump(), starts_on=today)
        self.bills.add(bill)
        await self.session.flush()
        return bill

    async def change_bill(
        self, bill_id: uuid.UUID, request: RegularExpenseRequest
    ) -> RegularExpense:
        """Change a regular bill; NotFoundError if it is not the user's (N2)."""
        bill = await self.bills.get(bill_id)
        if bill is None or bill.ends_on is not None:
            raise NotFoundError("No such regular bill.")
        for field, value in request.model_dump().items():
            setattr(bill, field, value)
        await self.session.flush()
        return bill

    async def end_bill(self, bill_id: uuid.UUID, today: date) -> None:
        """Stop a regular bill from next month; past months keep it, as an income's do."""
        bill = await self.bills.get(bill_id)
        if bill is None or bill.ends_on is not None:
            raise NotFoundError("No such regular bill.")
        if bill.starts_on.replace(day=1) == today.replace(day=1):
            await self.session.delete(bill)
        else:
            bill.ends_on = today
        await self.session.flush()

    async def regular_incomes(self) -> list[IncomeSource]:
        """The regular incomes still running (F23.17)."""
        return list(await self.sources.current())

    async def add_regular(self, request: IncomeSourceRequest, today: date) -> IncomeSource:
        """Start a regular income: it counts from this month on."""
        source = IncomeSource(**request.model_dump(), starts_on=today)
        self.sources.add(source)
        await self.session.flush()
        return source

    async def change_regular(
        self, source_id: uuid.UUID, request: IncomeSourceRequest
    ) -> IncomeSource:
        """Change a regular income's name, amount or day; NotFoundError if not the user's."""
        source = await self.sources.get(source_id)
        if source is None or source.ends_on is not None:
            raise NotFoundError("No such regular income.")
        for field, value in request.model_dump().items():
            setattr(source, field, value)
        await self.session.flush()
        return source

    async def end_regular(self, source_id: uuid.UUID, today: date) -> None:
        """Stop a regular income from next month on; this month and the past keep it.

        One started this very month never counted anywhere yet, so it simply goes.
        NotFoundError for one that is not the user's (N2).
        """
        source = await self.sources.get(source_id)
        if source is None or source.ends_on is not None:
            raise NotFoundError("No such regular income.")
        if source.starts_on.replace(day=1) == today.replace(day=1):
            await self.session.delete(source)
        else:
            source.ends_on = today
        await self.session.flush()

    async def add(self, request: IncomeRequest) -> Income:
        """Record a sum that came in, typed or confirmed from a document (`channel`).

        Whether it is taxed defaults by its kind (F23.16) — earnings are, the rest is not —
        and is kept even while the user does not pay their own taxes, so switching that on
        later reads the past right.
        """
        data = request.model_dump()
        if data["taxed"] is None:
            data["taxed"] = taxed_by_default(request.kind)
        income = Income(**data)
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
            if field == "taxed" and value is None:
                continue
            setattr(income, field, value)
        await self.session.flush()
        return income

    async def delete(self, income_id: uuid.UUID) -> None:
        if not await self.incomes.delete(income_id):
            raise NotFoundError("No such income.")

    async def pay_taxes(self, request: TaxPaymentRequest) -> TaxPayment:
        """Record taxes paid (F23.16): they leave the balance, never the spending."""
        payment = TaxPayment(**request.model_dump())
        self.tax_payments.add(payment)
        await self.session.flush()
        return payment

    async def tax_payments_of(self, first_day: date) -> list[TaxPayment]:
        """The month's tax payments, newest first."""
        last_day = date.fromordinal(next_month_start(first_day).toordinal() - 1)
        return list(await self.tax_payments.between(first_day, last_day))

    async def delete_tax_payment(self, payment_id: uuid.UUID) -> None:
        """Remove a tax payment; NotFoundError for one not the user's (N2)."""
        if not await self.tax_payments.delete(payment_id):
            raise NotFoundError("No such tax payment.")

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
