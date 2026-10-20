"""Where the money is: accounts, their ledgers and histories, and the money between them
(F23.15, ADR-0024)."""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import DomainError, NotFoundError, ProblemCode
from app.core.context import current_user_id
from app.domain.accounts import (
    AccountKind,
    Entry,
    EntryKind,
    Ledger,
    MoveKind,
    first_month,
    is_closed,
    ledger_of,
    months_between,
    next_month,
    tax_on,
)
from app.domain.income import Recurring, TaxRule
from app.domain.periods import DateRange
from app.models.account import Account, AccountMove, RegularTransfer
from app.models.household import HouseholdMember
from app.models.income import Income
from app.models.income_source import IncomeSource
from app.models.regular_expense import RegularExpense
from app.models.user import User
from app.repository.household import HouseholdRepository
from app.repository.money_accounts import (
    AccountMoneyRepository,
    AccountMoveRepository,
    AccountRepository,
    RegularTransferRepository,
)
from app.repository.regular_expense import RegularExpenseRepository
from app.services.household import refuse_child
from app.services.income import IncomeService, bill_rule, regular_rule, tax_rule


@dataclass(frozen=True)
class AccountView:
    """An account as the caller sees it: its ledger, and whose it is."""

    account: Account
    ledger: Ledger
    mine: bool
    added_by: str | None


@dataclass(frozen=True)
class Overview:
    """Every account the caller sees, and the money on them together."""

    accounts: list[AccountView]

    @property
    def total(self) -> Decimal:
        return sum((a.ledger.balance for a in self.accounts), Decimal("0.00"))

    @property
    def set_aside(self) -> Decimal:
        return sum((a.ledger.set_aside for a in self.accounts), Decimal("0.00"))


@dataclass(frozen=True)
class Family:
    """Who the caller keeps money with, and where each one's money lands by default."""

    me: uuid.UUID
    membership: HouseholdMember | None
    names: dict[uuid.UUID, str]
    own_card: dict[uuid.UUID, uuid.UUID]
    shared_card: uuid.UUID | None
    rules: dict[uuid.UUID, TaxRule]
    """The tax rule of each member who pays their own taxes (F23.16)."""

    @property
    def authors(self) -> list[uuid.UUID]:
        return list(self.names) or [self.me]

    def card_of(self, author: uuid.UUID, shared: bool) -> uuid.UUID | None:
        """The account a sum with no account of its own lands on (F23.15).

        Shared money lands on the family's purchase card; one's own on one's own card,
        else on the family's — the card one's purchases are paid from too.
        """
        if shared:
            return self.shared_card
        return self.own_card.get(author, self.shared_card)


class AccountService:
    """Accounts the caller sees and every sum on them, read as one ledger per account.

    Rules post nothing ahead: each month's occurrence of a regular income, bill or
    transfer is read from the rule on its day, unless the user changed that month's
    (an income confirming it, a move standing in for it). So a balance, a history and a
    month always agree, and stopping a rule never rewrites a past month.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.accounts = AccountRepository(session)
        self.moves = AccountMoveRepository(session)
        self.transfers = RegularTransferRepository(session)
        self.money = AccountMoneyRepository(session)

    # --- reading -------------------------------------------------------------------

    async def overview(self, today: date) -> Overview:
        """Every account the caller sees with its balance now."""
        accounts = list(await self.accounts.visible())
        if not accounts:
            return Overview([])
        family = await self._family()
        entries = await self._entries(accounts, family, today)
        return Overview(
            [
                AccountView(
                    a,
                    ledger_of(a.opening, [e for e in entries if e.account_id == a.id]),
                    a.user_id == family.me,
                    None if a.user_id == family.me else family.names.get(a.user_id),
                )
                for a in accounts
            ]
        )

    async def history(
        self, account_id: uuid.UUID, first_day: date, today: date
    ) -> tuple[AccountView, list[Entry]]:
        """One account and its entries in the month starting `first_day`, newest first."""
        accounts = list(await self.accounts.visible())
        account = next((a for a in accounts if a.id == account_id), None)
        if account is None:
            raise NotFoundError("No such account.")
        family = await self._family()
        entries = await self._entries(accounts, family, today)
        own = [e for e in entries if e.account_id == account_id]
        month = [
            e for e in own if e.day.replace(day=1) == first_day and e.kind != EntryKind.TAX_DUE
        ]
        view = AccountView(
            account,
            ledger_of(account.opening, own),
            account.user_id == family.me,
            None if account.user_id == family.me else family.names.get(account.user_id),
        )
        return view, sorted(month, key=lambda e: e.day, reverse=True)

    async def expected(self, today: date) -> list[Entry]:
        """ "About" incomes whose day has come this month, still to be confirmed (F_Check)."""
        overview = await self.overview(today)
        if not overview.accounts:
            return []
        family = await self._family()
        entries = await self._entries([a.account for a in overview.accounts], family, today)
        return [e for e in entries if e.kind == EntryKind.EXPECTED and not e.upcoming]

    # --- writing ---------------------------------------------------------------------

    async def create(
        self,
        *,
        name: str,
        kind: AccountKind,
        opening: Decimal,
        opening_on: date,
        tax_rate: Decimal | None,
        shared: bool,
        for_purchases: bool,
    ) -> Account:
        """Open an account; the first everyday card becomes the purchase card by itself.

        Only a business account sets tax aside; a shared one needs a household and an
        adult in it (F12.10).
        """
        household = await self._scope(shared)
        first = not any(
            a.for_purchases for a in await self.accounts.visible() if a.household_id == household
        )
        account = Account(
            name=name,
            kind=kind,
            opening=opening,
            opening_on=opening_on,
            tax_rate=tax_rate if kind == AccountKind.BUSINESS else None,
            household_id=household,
            # Only an everyday card becomes the purchase card by itself.
            for_purchases=kind != AccountKind.DEPOSIT
            and (for_purchases or (first and kind == AccountKind.PERSONAL)),
        )
        self.accounts.add(account)
        await self.session.flush()
        if account.for_purchases:
            await self._only_purchase_card(account)
        return account

    async def change(
        self,
        account_id: uuid.UUID,
        *,
        name: str,
        opening: Decimal,
        opening_on: date,
        tax_rate: Decimal | None,
        shared: bool,
        for_purchases: bool,
    ) -> Account:
        """Rename an account, correct where it started, its tax rate or whose it is."""
        account = await self._writable(account_id)
        if account.for_purchases and not for_purchases:
            await self._pin_unassigned(account)
        account.name = name
        account.opening = opening
        account.opening_on = opening_on
        account.tax_rate = tax_rate if account.kind == AccountKind.BUSINESS else None
        account.household_id = await self._scope(shared)
        account.for_purchases = account.kind != AccountKind.DEPOSIT and for_purchases
        await self.session.flush()
        if account.for_purchases:
            await self._only_purchase_card(account)
        return account

    async def remove(self, account_id: uuid.UUID, today: date) -> None:
        """Delete an account and the moves on it; sums that named it go back to the card.

        Removing the last card the user sees takes them back to a budget alone (F23.21):
        the starting balance kept before cards is forgotten, so no balance comes back, and
        their own regular incomes stop from next month — income is bookkeeping, and with no
        card it has nowhere to land. Past months keep what they had.
        """
        account = await self._writable(account_id)
        await self.session.delete(account)
        await self.session.flush()
        if not await self.accounts.visible():
            await self._back_to_budget(today)

    async def _back_to_budget(self, today: date) -> None:
        user = await self.session.get(User, _me())
        assert user is not None
        user.starting_balance = None
        user.balance_since = None
        incomes = IncomeService(self.session)
        for source in await incomes.regular_incomes():
            if source.user_id == user.id and source.household_id is None:
                await incomes.end_regular(source.id, today)
        await self.session.flush()

    async def money_in(
        self,
        account_id: uuid.UUID,
        *,
        amount: Decimal,
        source: str,
        received_on: date,
        today: date,
    ) -> Income:
        """Record money from outside on an account: income, taxed on a business account."""
        # Added on its own date even into a closed month, as a bank books a late payment.
        account = await self._writable(account_id)
        income = Income(
            amount=amount,
            source=source,
            received_on=received_on,
            kind="side" if account.kind == AccountKind.BUSINESS else "other",
            account_id=account.id,
            household_id=account.household_id,
            tax=tax_on(amount, account.tax_rate) or None,
            taxed=False,
            user_id=_me(),
        )
        self.session.add(income)
        await self.session.flush()
        return income

    async def change_income(
        self, income_id: uuid.UUID, amount: Decimal, received_on: date, today: date
    ) -> Income:
        """Correct an income on an account this month; its tax follows the account's rate."""
        income = await self.session.get(Income, income_id)
        visible = {a.id for a in await self.accounts.visible()}
        if income is None or income.account_id not in visible:
            raise NotFoundError("No such income.")
        account = await self._writable(income.account_id)
        self._open_month(income.received_on, today)
        self._open_month(received_on, today)
        income.amount = amount
        income.received_on = received_on
        income.tax = tax_on(amount, account.tax_rate) or None
        await self.session.flush()
        return income

    async def move(
        self,
        *,
        from_id: uuid.UUID,
        to_id: uuid.UUID,
        amount: Decimal,
        moved_on: date,
        today: date,
        name: str | None = None,
    ) -> AccountMove:
        """Move money between two accounts: neither income nor spending (F23.15)."""
        if from_id == to_id:
            raise DomainError("Choose two different accounts.", code=ProblemCode.SAME_ACCOUNT)
        source = await self._writable(from_id)
        target = await self._writable(to_id)
        move = AccountMove(
            kind=MoveKind.TRANSFER,
            name=name or f"{source.name} → {target.name}",
            amount=amount,
            moved_on=moved_on,
            from_account_id=source.id,
            to_account_id=target.id,
        )
        self.moves.add(move)
        await self.session.flush()
        return move

    async def adjust(self, account_id: uuid.UUID, balance: Decimal, today: date) -> AccountMove:
        """Bring an account to what the bank says today, by the difference."""
        overview = await self.overview(today)
        view = next((a for a in overview.accounts if a.account.id == account_id), None)
        if view is None:
            raise NotFoundError("No such account.")
        await self._writable(account_id)
        difference = balance - view.ledger.balance
        move = AccountMove(
            kind=MoveKind.ADJUSTMENT,
            name="Correction",
            amount=abs(difference),
            moved_on=today,
            to_account_id=account_id if difference >= 0 else None,
            from_account_id=None if difference >= 0 else account_id,
        )
        self.moves.add(move)
        await self.session.flush()
        return move

    async def change_move(
        self, move_id: uuid.UUID, amount: Decimal, moved_on: date, today: date
    ) -> AccountMove:
        """Correct a move of this month; earlier months are closed (MONTH_CLOSED)."""
        move = await self.moves.get(move_id)
        if move is None:
            raise NotFoundError("No such entry.")
        for account_id in (move.from_account_id, move.to_account_id):
            if account_id is not None:
                await self._writable(account_id)
        self._open_month(move.moved_on, today)
        self._open_month(moved_on, today)
        move.amount = amount
        move.moved_on = moved_on
        await self.session.flush()
        return move

    async def delete_move(self, move_id: uuid.UUID, today: date) -> None:
        """Remove a move of this month; earlier months are closed (MONTH_CLOSED)."""
        move = await self.moves.get(move_id)
        if move is None:
            raise NotFoundError("No such entry.")
        for account_id in (move.from_account_id, move.to_account_id):
            if account_id is not None:
                await self._writable(account_id)
        self._open_month(move.moved_on, today)
        await self.session.delete(move)
        await self.session.flush()

    async def set_occurrence(
        self, kind: str, rule_id: uuid.UUID, amount: Decimal, today: date
    ) -> AccountMove:
        """Change this month's bill or transfer made by a rule; 0 skips it this month."""
        first_day = today.replace(day=1)
        if kind == "bill":
            existing = await self.moves.for_month(first_day, bill_id=rule_id)
            rule = await self._bill(rule_id)
            day = bill_rule(rule).arrives_in(first_day)
            account_id = rule.account_id
            if account_id is None:
                raise DomainError("This bill is not on an account.", code=ProblemCode.DOMAIN_ERROR)
            await self._writable(account_id)
            move = existing or AccountMove(
                kind=MoveKind.BILL,
                name=rule.name,
                moved_on=day,
                from_account_id=account_id,
                bill_id=rule.id,
                amount=amount,
            )
        else:
            existing = await self.moves.for_month(first_day, rule_id=rule_id)
            transfer = await self.transfers.get(rule_id)
            if transfer is None:
                raise NotFoundError("No such monthly transfer.")
            await self._writable(transfer.from_account_id)
            day = Recurring(
                transfer.amount, transfer.day, transfer.starts_on, transfer.ends_on
            ).arrives_in(first_day)
            move = existing or AccountMove(
                kind=MoveKind.TRANSFER,
                name=transfer.name,
                moved_on=day,
                from_account_id=transfer.from_account_id,
                to_account_id=transfer.to_account_id,
                rule_id=transfer.id,
                amount=amount,
            )
        move.amount = amount
        if existing is None:
            self.moves.add(move)
        await self.session.flush()
        return move

    async def confirm(self, source_id: uuid.UUID, amount: Decimal, today: date) -> Income:
        """Say what an "about" income really brought this month; it then counts as that.

        More than usual is simply more this month — a bonus counts once, never changing
        the rule.
        """
        source = await self.session.get(IncomeSource, source_id)
        visible = {a.id for a in await self.accounts.visible()}
        if source is None or source.account_id not in visible:
            raise NotFoundError("No such regular income.")
        account = await self._writable(source.account_id)
        first_day = today.replace(day=1)
        day = regular_rule(source).arrives_in(first_day)
        existing = await self.session.scalar(
            select(Income).where(
                Income.source_id == source.id,
                Income.received_on >= first_day,
                Income.received_on < next_month(first_day),
            )
        )
        income = existing or Income(
            user_id=_me(),
            source=source.name,
            kind="salary",
            received_on=day,
            account_id=account.id,
            household_id=source.household_id,
            source_id=source.id,
            taxed=False,
            amount=amount,
        )
        income.amount = amount
        income.tax = tax_on(amount, account.tax_rate) or None
        if existing is None:
            self.session.add(income)
        await self.session.flush()
        return income

    async def add_transfer_rule(
        self,
        *,
        from_id: uuid.UUID,
        to_id: uuid.UUID,
        amount: Decimal,
        day: int | None,
        today: date,
        name: str | None,
    ) -> RegularTransfer:
        """Move money every month by itself, from the first day still to come (F23.15)."""
        if from_id == to_id:
            raise DomainError("Choose two different accounts.", code=ProblemCode.SAME_ACCOUNT)
        source = await self._writable(from_id)
        target = await self._writable(to_id)
        start = first_month(day, today)
        rule = RegularTransfer(
            name=name or f"To “{target.name}”",
            amount=amount,
            day=day,
            starts_on=today if start <= today else start,
            from_account_id=source.id,
            to_account_id=target.id,
        )
        self.transfers.add(rule)
        await self.session.flush()
        return rule

    async def change_transfer_rule(
        self, rule_id: uuid.UUID, *, amount: Decimal, day: int | None, name: str
    ) -> RegularTransfer:
        """Change a monthly transfer from this month on; earlier months keep the old one."""
        rule = await self.transfers.get(rule_id)
        if rule is None or rule.ends_on is not None:
            raise NotFoundError("No such monthly transfer.")
        await self._writable(rule.from_account_id)
        this_month = datetime.now(UTC).date().replace(day=1)
        if rule.starts_on < this_month:
            # Changed in place, earlier months would be read with the new amount: the old
            # version ends with last month and a new one carries on (closed months, F23.15).
            copy = RegularTransfer(
                user_id=rule.user_id,
                name=rule.name,
                amount=rule.amount,
                day=rule.day,
                starts_on=this_month,
                from_account_id=rule.from_account_id,
                to_account_id=rule.to_account_id,
            )
            rule.ends_on = this_month - timedelta(days=1)
            self.session.add(copy)
            await self.session.flush()
            await self.session.execute(
                update(AccountMove)
                .where(AccountMove.rule_id == rule.id, AccountMove.moved_on >= this_month)
                .values(rule_id=copy.id)
            )
            rule = copy
        rule.amount, rule.day, rule.name = amount, day, name or rule.name
        await self.session.flush()
        return rule

    async def end_transfer_rule(self, rule_id: uuid.UUID, today: date) -> None:
        """Stop a monthly transfer from next month; one started this month simply goes."""
        rule = await self.transfers.get(rule_id)
        if rule is None or rule.ends_on is not None:
            raise NotFoundError("No such monthly transfer.")
        await self._writable(rule.from_account_id)
        if rule.starts_on >= today.replace(day=1):
            await self.session.delete(rule)
        else:
            rule.ends_on = today
        await self.session.flush()

    async def transfer_rules(self) -> list[RegularTransfer]:
        """The monthly transfers still running."""
        return [r for r in await self.transfers.running() if r.ends_on is None]

    # --- the ledger --------------------------------------------------------------------

    async def _entries(self, accounts: list[Account], family: Family, today: date) -> list[Entry]:
        """Every entry on the given accounts from their opening day up to this month's end."""
        seen = {a.id: a for a in accounts}
        start = min(a.opening_on for a in accounts)
        end = next_month(today.replace(day=1))
        entries: list[Entry] = []

        def add(account_id: uuid.UUID | None, day: date, **fields: object) -> None:
            account = seen.get(account_id) if account_id else None
            if account is None or day < account.opening_on:
                return
            entries.append(Entry(account_id=account.id, day=day, **fields))  # type: ignore[arg-type]

        incomes = await self.money.incomes(family.authors, today)
        confirmed = {(i.source_id, i.received_on.replace(day=1)) for i in incomes if i.source_id}
        for income in incomes:
            target = income.account_id or family.card_of(
                income.user_id, income.household_id is not None
            )
            add(
                target,
                income.received_on,
                kind=EntryKind.INCOME,
                name=self._name(income.source, income.user_id, income.household_id, family),
                amount=income.amount,
                tax=income.tax
                or self._own_tax(income.amount, income.taxed, income.user_id, target, seen, family),
                ref=self._ref("income", income.id, income.user_id, income.household_id, family),
                by_rule=income.source_id is not None,
            )

        for source in await self.money.sources(family.authors):
            target = source.account_id or family.card_of(
                source.user_id, source.household_id is not None
            )
            if target not in seen:
                continue
            rule = regular_rule(source)
            for month in months_between(max(start, source.starts_on), today):
                if (source.id, month) in confirmed:
                    continue
                for day in rule.days_in(month):
                    add(
                        target,
                        day,
                        kind=EntryKind.EXPECTED if source.about else EntryKind.INCOME,
                        name=self._name(source.name, source.user_id, source.household_id, family),
                        amount=source.amount,
                        tax=tax_on(source.amount, seen[target].tax_rate)
                        or self._own_tax(
                            source.amount, source.taxed, source.user_id, target, seen, family
                        ),
                        ref=self._ref(
                            "source", source.id, source.user_id, source.household_id, family
                        ),
                        by_rule=True,
                        upcoming=day > today,
                    )

        moves = list(await self.moves.until(end))
        changed = {(m.bill_id or m.rule_id, m.moved_on.replace(day=1)) for m in moves}
        for bill in await self.money.bills(family.authors):
            target = bill.account_id or family.card_of(bill.user_id, bill.household_id is not None)
            if target not in seen:
                continue
            rule = bill_rule(bill)
            for month in months_between(max(start, bill.starts_on), today):
                if (bill.id, month) in changed:
                    continue
                for day in rule.days_in(month):
                    add(
                        target,
                        day,
                        kind=EntryKind.BILL,
                        name=self._name(bill.name, bill.user_id, bill.household_id, family),
                        amount=-bill.amount,
                        ref=self._ref("bill", bill.id, bill.user_id, bill.household_id, family),
                        by_rule=True,
                        upcoming=day > today,
                    )

        for transfer in await self.transfers.running():
            rule = Recurring(transfer.amount, transfer.day, transfer.starts_on, transfer.ends_on)
            for month in months_between(max(start, transfer.starts_on), today):
                if not rule.runs_in(month) or (transfer.id, month) in changed:
                    continue
                day = rule.arrives_in(month)
                common = {"name": transfer.name, "ref": ("rule", transfer.id), "by_rule": True}
                add(
                    transfer.from_account_id,
                    day,
                    kind=EntryKind.TRANSFER_OUT,
                    amount=-transfer.amount,
                    upcoming=day > today,
                    **common,
                )
                add(
                    transfer.to_account_id,
                    day,
                    kind=EntryKind.TRANSFER_IN,
                    amount=transfer.amount,
                    upcoming=day > today,
                    **common,
                )

        for move in moves:
            upcoming = move.moved_on > today
            common = {
                "name": move.name,
                "ref": ("move", move.id),
                "by_rule": bool(move.bill_id or move.rule_id),
                "upcoming": upcoming,
            }
            if move.kind == MoveKind.ADJUSTMENT:
                sign = Decimal(1) if move.to_account_id else Decimal(-1)
                add(
                    move.to_account_id or move.from_account_id,
                    move.moved_on,
                    kind=EntryKind.ADJUSTMENT,
                    amount=sign * move.amount,
                    **common,
                )
            elif move.kind == MoveKind.BILL:
                add(
                    move.from_account_id,
                    move.moved_on,
                    kind=EntryKind.BILL,
                    amount=-move.amount,
                    **common,
                )
            else:
                add(
                    move.from_account_id,
                    move.moved_on,
                    kind=EntryKind.TRANSFER_OUT,
                    amount=-move.amount,
                    **common,
                )
                add(
                    move.to_account_id,
                    move.moved_on,
                    kind=EntryKind.TRANSFER_IN,
                    amount=move.amount,
                    **common,
                )

        for author, own_rule in family.rules.items():
            card = family.card_of(author, False)
            if not own_rule.fixed or card not in seen:
                continue
            for month in months_between(start, today):
                add(
                    card,
                    max(month, seen[card].opening_on),
                    kind=EntryKind.TAX_DUE,
                    name="",
                    amount=Decimal("0.00"),
                    tax=own_rule.fixed,
                )

        for payment in await self.money.tax_payments(family.authors, today):
            target = payment.account_id or family.card_of(payment.user_id, False)
            add(
                target,
                payment.paid_on,
                kind=EntryKind.TAX_PAID,
                name="Taxes",
                amount=-payment.amount,
                ref=None,
            )

        hidden: dict[tuple[uuid.UUID | None, date], tuple[Decimal, int]] = {}
        # An account opened after the caller's today has had no purchases yet.
        bought = (
            await self.money.purchases(family.authors, DateRange(start, today))
            if start <= today
            else []
        )
        for buyer, day, private, count, paid in bought:
            target = family.card_of(buyer, False)
            if private and buyer != family.me:
                # Another member's private receipts say no day (ADR-0017): one sum a month.
                key = (target, day.replace(day=1))
                total, n = hidden.get(key, (Decimal(0), 0))
                hidden[key] = (total + paid, n + count)
                continue
            add(
                target,
                day,
                kind=EntryKind.PURCHASES,
                name="Purchases",
                amount=-paid,
                count=count,
                author=None if buyer == family.me else family.names.get(buyer),
            )
        for (target, month), (paid, count) in hidden.items():
            last = min(next_month(month), today + timedelta(days=1)) - timedelta(days=1)
            add(
                target,
                max(last, month),
                kind=EntryKind.PURCHASES,
                name="Private",
                amount=-paid,
                count=count,
                author="private",
            )
        return entries

    @staticmethod
    def _own_tax(
        amount: Decimal,
        taxed: bool,
        author: uuid.UUID,
        target: uuid.UUID | None,
        seen: dict[uuid.UUID, Account],
        family: Family,
    ) -> Decimal:
        """Tax set aside by the author's own rule (F23.16), on an account without a rate."""
        rule = family.rules.get(author)
        account = seen.get(target) if target else None
        if not taxed or rule is None or account is None or account.tax_rate:
            return Decimal("0.00")
        return rule.on(amount)

    def _name(
        self, name: str, author: uuid.UUID, household: uuid.UUID | None, family: Family
    ) -> str:
        """A line's name; another member's own money on a shared card says only whose."""
        if author == family.me or household is not None:
            return name
        return family.names.get(author, "")

    @staticmethod
    def _ref(
        kind: str,
        row_id: uuid.UUID,
        author: uuid.UUID,
        household: uuid.UUID | None,
        family: Family,
    ) -> tuple[str, uuid.UUID] | None:
        """What a line is changed through; another member's own money is not the caller's
        to change, so it has none."""
        if author == family.me or household is not None:
            return (kind, row_id)
        return None

    async def _family(self) -> Family:
        me = _me()
        membership = await HouseholdRepository(self.session).membership_of(me)
        names = (
            {m.user_id: m.user.first_name for m in membership.household.members}
            if membership
            else {me: ""}
        )
        cards = (
            (
                await self.session.execute(
                    select(Account).where(
                        Account.for_purchases.is_(True),
                        or_(
                            and_(Account.user_id.in_(list(names)), Account.household_id.is_(None)),
                            Account.household_id
                            == (membership.household_id if membership else None),
                        ),
                    )
                )
            )
            .scalars()
            .all()
        )
        own = {c.user_id: c.id for c in cards if c.household_id is None}
        shared = next((c.id for c in cards if c.household_id is not None), None)
        users = (
            [m.user for m in membership.household.members]
            if membership
            else [u for u in [await self.session.get(User, me)] if u is not None]
        )
        rules = {u.id: rule for u in users if (rule := tax_rule(u)) is not None}
        return Family(me, membership, names, own, shared, rules)

    async def _scope(self, shared: bool) -> uuid.UUID | None:
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

    async def _writable(self, account_id: uuid.UUID) -> Account:
        """An account the caller sees and may change: a child changes no shared one."""
        account = await self.accounts.get(account_id)
        if account is None:
            raise NotFoundError("No such account.")
        if account.household_id is not None:
            refuse_child(await HouseholdRepository(self.session).membership_of(_me()))
        return account

    async def _bill(self, bill_id: uuid.UUID) -> RegularExpense:
        bill = await RegularExpenseRepository(self.session).get(bill_id)
        if bill is None:
            raise NotFoundError("No such regular bill.")
        return bill

    async def _only_purchase_card(self, card: Account) -> None:
        """One purchase card per person and one per family: marking one unmarks the other."""
        for other in await self.accounts.visible():
            same_scope = (
                other.household_id == card.household_id
                if card.household_id
                else other.household_id is None and other.user_id == card.user_id
            )
            if other.id != card.id and same_scope and other.for_purchases:
                await self._pin_unassigned(other)
                other.for_purchases = False
        await self.session.flush()

    async def _pin_unassigned(self, card: Account) -> None:
        """Keep on `card` what reached it only for being the purchase card (F23.21).

        Bills, regular incomes and incomes on no card are read onto whichever card is the
        purchase card. Before it stops being one, they are written onto it, so its history
        stays as it was and nothing moves to the next card's past.
        """
        for model in (RegularExpense, IncomeSource, Income):
            scope = (
                model.household_id == card.household_id
                if card.household_id
                else and_(model.household_id.is_(None), model.user_id == card.user_id)
            )
            await self.session.execute(
                update(model).where(model.account_id.is_(None), scope).values(account_id=card.id)
            )

    @staticmethod
    def _open_month(day: date, today: date) -> None:
        """Refuse changing or removing what a closed month holds; adding to it is allowed."""
        if is_closed(day, today):
            raise DomainError(
                "That month is closed: only this month's entries can change.",
                code=ProblemCode.MONTH_CLOSED,
            )


def _me() -> uuid.UUID:
    me = current_user_id.get()
    if me is None:
        from app.api.errors import AuthenticationError

        raise AuthenticationError("No user context available.")
    return me
