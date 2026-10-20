"""Money coming in (F23.10)."""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import DomainError, NotFoundError, ProblemCode
from app.core.context import current_user_id
from app.domain.accounts import AccountKind, first_month, is_closed, tax_on
from app.domain.income import (
    IncomeChannel,
    MonthIncome,
    Recurring,
    TaxRule,
    month_income,
    taxed_by_default,
)
from app.domain.quota import next_month_start
from app.models.account import Account, AccountMove
from app.models.income import Income
from app.models.income_source import IncomeSource
from app.models.pending_income import PendingIncome
from app.models.regular_expense import RegularExpense
from app.models.tax_payment import TaxPayment
from app.models.user import User
from app.repository.household import HouseholdRepository
from app.repository.income import IncomeRepository
from app.repository.income_source import IncomeSourceRepository
from app.repository.money_accounts import AccountRepository, purchase_card
from app.repository.pending_income import PendingIncomeRepository
from app.repository.regular_expense import RegularExpenseRepository
from app.repository.tax_payment import TaxPaymentRepository
from app.schemas.income import (
    IncomeRequest,
    IncomeSourceRequest,
    RegularExpenseRequest,
    TaxPaymentRequest,
)
from app.services.household import refuse_child


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
class Whose:
    """Whose a sum is, for the caller (F12.8): the household's, and who wrote it."""

    shared: bool
    mine: bool
    added_by: str | None


@dataclass(frozen=True)
class Sharing:
    """Who is in the caller's household, by name, to say whose each sum is (F12.8)."""

    me: uuid.UUID
    names: dict[uuid.UUID, str]

    def whose(self, row: Income | IncomeSource | RegularExpense) -> Whose:
        """Shared or not, and who wrote it when it was not the caller."""
        mine = row.user_id == self.me
        return Whose(
            row.household_id is not None, mine, None if mine else self.names.get(row.user_id)
        )


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
        confirmed = {e.source_id for e in entries if e.source_id}
        regular = [
            s
            for s in await self.sources.running_since(first_day)
            if regular_rule(s).runs_in(first_day) and s.id not in confirmed
        ]
        # An account with its own rate sets tax aside by it (F23.15); on any other the
        # user's own rule does, as it did before accounts.
        rates = {a.id: a.tax_rate for a in await AccountRepository(self.session).visible()}

        def by_user(account_id: uuid.UUID | None) -> bool:
            return not rates.get(account_id) if account_id else True

        set_aside = sum(
            (e.tax or Decimal(0) for e in entries if not by_user(e.account_id)), Decimal(0)
        ) + sum(
            (
                tax_on(s.amount, rates[s.account_id])
                for s in regular
                if s.account_id is not None and not by_user(s.account_id)
            ),
            Decimal(0),
        )
        income = month_income(
            ((e.amount, e.taxed and by_user(e.account_id)) for e in entries),
            user.usual_income,
            tax_rule(user),
            recurring=((s.amount, s.taxed and by_user(s.account_id)) for s in regular),
            set_aside=set_aside,
        )
        paid = await self.tax_payments.total(first_day, last_day)
        bills = [
            b for b in await self.bills.running_since(first_day) if bill_rule(b).runs_in(first_day)
        ]
        return MonthIncomeView(first_day, income, entries, paid, regular, bills)

    async def _scope(self, shared: bool) -> uuid.UUID | None:
        """The household a sum goes to when shared (F12.8), None when it is the caller's.

        DomainError when it is meant to be shared but the caller has no household;
        PermissionDeniedError when the caller is a child in it (F12.10).
        """
        if not shared:
            return None
        membership = await HouseholdRepository(self.session).membership_of(_me())
        refuse_child(membership)
        if membership is None:
            raise DomainError(
                "Only a member of a household can share with it.",
                code=ProblemCode.NOT_IN_HOUSEHOLD,
            )
        return membership.household_id

    async def _place(
        self, shared: bool, account_id: uuid.UUID | None
    ) -> tuple[uuid.UUID | None, Account | None]:
        """The household and account a sum goes to (F12.8, F23.15).

        Every sum is on an account: left out, it goes on the caller's purchase card —
        their own, else the family's — opened for them when there is none, and is shared
        as `shared` says. On an account the user picked it is shared exactly when the
        account is. NotFoundError for an account the caller does not see (N2); a child
        shares nothing and puts nothing on a shared account.
        """
        accounts = AccountRepository(self.session)
        if account_id is None:
            # Landed on the purchase card, a sum stays as shared as the user said it is.
            household = await self._scope(shared)
            visible = await accounts.visible()
            card = purchase_card(visible, _me()) or await self._open_card(shared, first=not visible)
            return household, card
        account = await accounts.get(account_id)
        if account is None:
            raise NotFoundError("No such account.")
        if account.household_id is not None:
            refuse_child(await HouseholdRepository(self.session).membership_of(_me()))
        return account.household_id, account

    async def _open_card(self, shared: bool, *, first: bool) -> Account:
        """Open the card a user's money lands on, when they have none (F23.15).

        The first account carries over the balance as the user started it (F23.14), so
        opening it changes no figure; otherwise it starts at zero on the 1st of this month,
        so a sum entered for an earlier day of it still counts. A sum meant for the family
        opens the family's card.
        """
        user = await self.session.get(User, _me())
        assert user is not None
        household = await self._scope(shared)
        # The first account takes over the balance as it was started (F23.14): the same
        # amount on the same day, so the ledger replays exactly what the balance counted.
        if first and user.starting_balance is not None and user.balance_since is not None:
            opening, opening_on = user.starting_balance, user.balance_since
        else:
            opening, opening_on = Decimal("0.00"), datetime.now(UTC).date().replace(day=1)
        card = Account(
            user_id=user.id,
            household_id=household,
            name=CARD_NAMES[bool(household)].get(
                user.language or "en", CARD_NAMES[bool(household)]["en"]
            ),
            kind=AccountKind.PERSONAL,
            opening=opening,
            opening_on=opening_on,
            for_purchases=True,
        )
        self.session.add(card)
        await self.session.flush()
        return card

    async def _from_this_month[R: (IncomeSource, RegularExpense)](self, rule: R) -> R:
        """The rule a change applies to: itself if it started this month, else a new version.

        A rule is read again for every month it runs, so changing it in place would rewrite
        months already closed (F23.15). One that started earlier ends with last month and
        a copy carries on from this month, taking over this month's confirmations and
        changed occurrences, so nothing counts twice; the change is then made to the copy.
        """
        this_month = datetime.now(UTC).date().replace(day=1)
        if rule.starts_on >= this_month:
            return rule
        copy = type(rule)(
            **{
                column.key: getattr(rule, column.key)
                for column in type(rule).__table__.columns
                if column.key not in {"id", "created_at", "updated_at", "starts_on", "ends_on"}
            },
            starts_on=this_month,
        )
        rule.ends_on = this_month - timedelta(days=1)
        self.session.add(copy)
        await self.session.flush()
        if isinstance(rule, IncomeSource):
            await self.session.execute(
                update(Income)
                .where(Income.source_id == rule.id, Income.received_on >= this_month)
                .values(source_id=copy.id)
            )
        else:
            await self.session.execute(
                update(AccountMove)
                .where(AccountMove.bill_id == rule.id, AccountMove.moved_on >= this_month)
                .values(bill_id=copy.id)
            )
        return copy

    async def _may_change(self, row: Income | IncomeSource | RegularExpense) -> None:
        """A shared row is changed by the household's adults only (F12.10)."""
        if row.household_id is not None:
            refuse_child(await HouseholdRepository(self.session).membership_of(_me()))

    async def sharing(self) -> Sharing:
        """Who is in the caller's household, by name (F12.8)."""
        me = _me()
        membership = await HouseholdRepository(self.session).membership_of(me)
        if membership is None:
            return Sharing(me, {})
        return Sharing(me, {m.user_id: m.user.first_name for m in membership.household.members})

    async def regular_bills(self) -> list[RegularExpense]:
        """The regular bills still running (F23.18)."""
        return list(await self.bills.current())

    async def add_bill(self, request: RegularExpenseRequest, today: date) -> RegularExpense:
        """Start a regular bill: it counts from this month on."""
        household, account = await self._place(request.shared, request.account_id)
        bill = RegularExpense(
            **request.model_dump(exclude={"shared", "account_id"}),
            account_id=account.id if account else None,
            household_id=household,
            starts_on=_starts_on(request.day, today),
        )
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
        await self._may_change(bill)
        bill = await self._from_this_month(bill)
        for field, value in request.model_dump(exclude={"shared"}).items():
            setattr(bill, field, value)
        bill.household_id, account = await self._place(request.shared, request.account_id)
        bill.account_id = account.id if account else None
        await self.session.flush()
        return bill

    async def end_bill(self, bill_id: uuid.UUID, today: date) -> None:
        """Stop a regular bill from next month; past months keep it, as an income's do."""
        bill = await self.bills.get(bill_id)
        if bill is None or bill.ends_on is not None:
            raise NotFoundError("No such regular bill.")
        await self._may_change(bill)
        if bill.starts_on.replace(day=1) >= today.replace(day=1):
            await self.session.delete(bill)
        else:
            bill.ends_on = today
        await self.session.flush()

    async def regular_incomes(self) -> list[IncomeSource]:
        """The regular incomes still running (F23.17)."""
        return list(await self.sources.current())

    async def add_regular(self, request: IncomeSourceRequest, today: date) -> IncomeSource:
        """Start a regular income: from this month, or the next when its day has passed."""
        household, account = await self._place(request.shared, request.account_id)
        source = IncomeSource(
            **request.model_dump(exclude={"shared", "account_id"}),
            account_id=account.id if account else None,
            household_id=household,
            starts_on=_starts_on(request.day, today),
        )
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
        await self._may_change(source)
        source = await self._from_this_month(source)
        for field, value in request.model_dump(exclude={"shared"}).items():
            setattr(source, field, value)
        source.household_id, account = await self._place(request.shared, request.account_id)
        source.account_id = account.id if account else None
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
        await self._may_change(source)
        if source.starts_on.replace(day=1) >= today.replace(day=1):
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
        data = request.model_dump(exclude={"shared"})
        if data["taxed"] is None:
            data["taxed"] = taxed_by_default(request.kind)
        # A late document may land in a closed month on its own date: adding is allowed,
        # only changing or removing what a closed month holds is not (F23.15).
        household, account = await self._place(request.shared, request.account_id)
        data["account_id"] = account.id if account else None
        income = Income(
            **data,
            household_id=household,
            tax=tax_on(request.amount, account.tax_rate) or None if account else None,
        )
        self.incomes.add(income)
        await self.session.flush()
        return income

    async def update(self, income_id: uuid.UUID, request: IncomeRequest) -> Income:
        """Change an entry; NotFoundError for one not the user's (N2)."""
        income = await self.incomes.get(income_id)
        if income is None:
            raise NotFoundError("No such income.")
        await self._may_change(income)
        if income.account_id is not None:
            _open_month(income.received_on)
        # How an entry came in stays as it was: correcting it does not make it typed.
        for field, value in request.model_dump(exclude={"channel", "shared"}).items():
            if field == "taxed" and value is None:
                continue
            setattr(income, field, value)
        income.household_id, account = await self._place(request.shared, request.account_id)
        income.account_id = account.id if account else None
        if account is not None:
            _open_month(income.received_on)
        income.tax = tax_on(income.amount, account.tax_rate) or None if account else None
        await self.session.flush()
        return income

    async def delete(self, income_id: uuid.UUID) -> None:
        """Remove an entry; NotFoundError for one not the user's (N2), refused to a child
        when it is shared (F12.10)."""
        income = await self.incomes.get(income_id)
        if income is None:
            raise NotFoundError("No such income.")
        await self._may_change(income)
        if income.account_id is not None:
            _open_month(income.received_on)
        await self.incomes.delete(income_id)

    async def pay_taxes(self, request: TaxPaymentRequest) -> TaxPayment:
        """Record taxes paid (F23.16): they leave the balance, never the spending."""
        _, account = await self._place(False, request.account_id)
        payment = TaxPayment(
            **request.model_dump(exclude={"account_id"}),
            account_id=account.id if account else None,
        )
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


CARD_NAMES = {
    False: {"en": "My card", "uk": "Моя картка", "pl": "Moja karta"},
    True: {"en": "Our card", "uk": "Наша картка", "pl": "Nasza karta"},
}
"""What a card opened by itself is called, in the user's language."""


def _starts_on(day: int | None, today: date) -> date:
    """When a rule made `today` starts: today, or the 1st of next month when its day has
    already passed this month — a rule never posts on a day gone by (F23.15)."""
    start = first_month(day, today)
    return today if start <= today else start


def _open_month(day: date) -> None:
    """Refuse changing what an account shows for a closed month (F23.15)."""
    if is_closed(day, datetime.now(UTC).date()):
        raise DomainError(
            "That month is closed: only this month's entries can change.",
            code=ProblemCode.MONTH_CLOSED,
        )


def _me() -> uuid.UUID:
    """The signed-in user, as the request context holds them."""
    me = current_user_id.get()
    if me is None:
        from app.api.errors import AuthenticationError

        raise AuthenticationError("No user context available.")
    return me
