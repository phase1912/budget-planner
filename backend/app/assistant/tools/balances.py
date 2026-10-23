"""A card's balance in words (F21.10): set right to what the bank says, money put on or
taken off once, moved between two cards. The rules of the Accounts screen hold (ADR-0024):
a correction is neither income nor spending, money in is income, a move is neither."""

import uuid
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.api.errors import DomainError, ProblemCode
from app.assistant.tools.accounts import find_account
from app.assistant.tools.base import Amount, Balance, FormField, ToolContext, Writer, as_id
from app.assistant.tools.expenses import FALLBACK_CATEGORIES
from app.models.account import Account
from app.services.manual_expense import ManualExpense, record_expense
from app.services.money_accounts import AccountService

Way = Literal["correct", "spending"]
WAYS: tuple[str, ...] = ("correct", "spending")

UNENTERED = {"uk": "Невнесені покупки", "pl": "Niewpisane zakupy"}
"""What purchases never entered are called on the receipts list, in the user's language."""


async def _balance(ctx: ToolContext, account: Account) -> Decimal:
    overview = await AccountService(ctx.session).overview(ctx.today)
    return next(v.ledger.balance for v in overview.accounts if v.account.id == account.id)


def _why_not_spending(account: Account, now: Decimal, balance: Decimal) -> str | None:
    """Why a difference cannot be recorded as purchases: the bank shows more, or the card
    is not the one purchases are paid from — spending recorded would lower that one."""
    if balance >= now:
        return (
            f"the bank shows more than the {now} on {account.name}: only a correction, or "
            "money in with add_money"
        )
    if not account.for_purchases:
        return (
            f"purchases are paid from the purchase card, not {account.name}: only a "
            "correction for this one"
        )
    return None


class SyncArgs(BaseModel):
    """What the bank says is on a card."""

    account: str = Field(min_length=1, description="The card or account, by name")
    balance: Balance = Field(description="What the bank says is on it now")
    way: Way | None = Field(
        None,
        description=(
            "correct: only set the balance; spending: the difference was purchases not "
            "entered, counted in the month's budget. Leave out unless the user said which"
        ),
    )
    category: str | None = Field(None, description="spending only: one of the user's categories")


class BalanceCard(BaseModel):
    """A balance set right, as the user approves it: how, and to what."""

    account_id: uuid.UUID
    target: str
    bank_balance: Balance
    way: Way
    category_id: uuid.UUID | None = None
    description: str = Field(min_length=1, max_length=255)


class SyncBalance(Writer):
    """A card brought to what the bank says, the user choosing how (F21.10.2): a correction
    only, or the difference recorded as purchases never entered — spent today, counted in
    the budget, which only the purchase card can take."""

    name = "sync_balance"
    description = (
        "Propose setting a card's balance to what the bank says. Pass way only when the user "
        "said it — 'just fix it' is correct, 'purchases I did not enter' is spending; "
        "otherwise leave it out and the card asks them."
    )
    args = SyncArgs
    card_kind = "balance"
    card = BalanceCard
    form = (
        FormField("target", "target"),
        FormField("bank_balance", "balance"),
        FormField("way", "choice", options=WAYS),
        FormField("category_id", "category", required=False),
        FormField("description", "text"),
    )

    async def check(self, ctx: ToolContext, args: SyncArgs) -> str | None:
        account, error = await find_account(ctx, args.account)
        if account is None:
            return error
        now = await _balance(ctx, account)
        if args.balance == now:
            return f"{account.name} already has {now}: nothing to change"
        return _why_not_yet(account, now, args.balance, args.way)

    async def propose(self, ctx: ToolContext, args: SyncArgs) -> dict[str, Any]:
        account, _ = await find_account(ctx, args.account)
        assert account is not None
        now = await _balance(ctx, account)
        return {
            "account_id": str(account.id),
            "target": f"{account.name}: {now:.2f} → {args.balance:.2f} {ctx.user.currency}",
            "bank_balance": str(args.balance),
            **await _how(
                ctx, args.way, args.category, ask=_asks(account, now, args.balance, args.way)
            ),
        }

    async def save(self, ctx: ToolContext, fields: BalanceCard) -> str:
        return await _settle(ctx, fields.account_id, lambda now: fields.bank_balance, fields)


class TakeArgs(BaseModel):
    """Money taken off a card once — cash out, a payment the app did not see."""

    account: str = Field(min_length=1, description="The card or account, by name")
    amount: Amount
    way: Way | None = Field(
        None,
        description=(
            "spending: it was spent, counted in the month's budget; correct: it only leaves "
            "the card. Leave out unless the user said which"
        ),
    )
    category: str | None = Field(None, description="spending only: one of the user's categories")


class TakeCard(BaseModel):
    """A sum taken off as the user approves it: how much, and how it is counted."""

    account_id: uuid.UUID
    amount: Amount
    way: Way
    category_id: uuid.UUID | None = None
    description: str = Field(min_length=1, max_length=255)


class TakeMoney(Writer):
    """A sum taken off a card once, with the same choice as a balance set right. The card
    keeps the sum, not the balance it leads to, so money arriving before approval stays."""

    name = "take_money"
    description = (
        "Propose taking a sum off a card once. Pass way only when the user said whether it "
        "was spent or only leaves the card; otherwise leave it out and the card asks them."
    )
    args = TakeArgs
    card_kind = "money_out"
    card = TakeCard
    form = (
        FormField("account_id", "account"),
        FormField("amount", "amount"),
        FormField("way", "choice", options=WAYS),
        FormField("category_id", "category", required=False),
        FormField("description", "text"),
    )

    async def check(self, ctx: ToolContext, args: TakeArgs) -> str | None:
        account, error = await find_account(ctx, args.account)
        if account is None:
            return error
        now = await _balance(ctx, account)
        return _why_not_yet(account, now, now - args.amount, args.way)

    async def propose(self, ctx: ToolContext, args: TakeArgs) -> dict[str, Any]:
        account, _ = await find_account(ctx, args.account)
        assert account is not None
        now = await _balance(ctx, account)
        return {
            "account_id": str(account.id),
            "amount": str(args.amount),
            **await _how(
                ctx, args.way, args.category, ask=_asks(account, now, now - args.amount, args.way)
            ),
        }

    async def save(self, ctx: ToolContext, fields: TakeCard) -> str:
        return await _settle(ctx, fields.account_id, lambda now: now - fields.amount, fields)


def _why_not_yet(account: Account, now: Decimal, balance: Decimal, way: Way | None) -> str | None:
    """Why the call cannot become a card: purchases the account cannot take. A way not said
    is no reason — the card then asks the user how it counts (F21.10.2)."""
    return _why_not_spending(account, now, balance) if way == "spending" else None


def _asks(account: Account, now: Decimal, balance: Decimal, way: Way | None) -> bool:
    """Whether the card leaves the way for the user to choose: a drop on the card paid from,
    where it may be purchases never entered, and the user did not say which."""
    return way is None and balance < now and account.for_purchases


async def _how(
    ctx: ToolContext, way: Way | None, category: str | None, *, ask: bool = False
) -> dict[str, Any]:
    """The card's choice: the way — left empty for the user to choose when `ask` — and for
    purchases the category — the one named, else the catch-all — and what the receipts list
    calls them."""
    categories = await ctx.categories()
    wanted = (category or "").strip().lower()
    chosen = next((c for c in categories if c.name.lower() == wanted), None) or next(
        (c for c in categories if c.name in FALLBACK_CATEGORIES), None
    )
    return {
        "way": None if ask else way or "correct",
        "category_id": str(chosen.id) if chosen else None,
        "description": UNENTERED.get(ctx.user.language or "en", "Purchases not entered"),
    }


async def _settle(
    ctx: ToolContext,
    account_id: Any,
    after: Callable[[Decimal], Decimal],
    fields: BalanceCard | TakeCard,
) -> str:
    """Bring an approved card's account to `after` its balance now: by a correction, or by
    purchases never entered, spent today and counted in the budget.

    Worked out on approval, since the balance may have moved since the card was made.
    Raises DomainError (invalid_card) when the purchases no longer hold.
    """
    overview = await AccountService(ctx.session).overview(ctx.today)
    view = next((v for v in overview.accounts if v.account.id == as_id(account_id)), None)
    if view is None:
        raise DomainError("That card is gone.", code=ProblemCode.INVALID_CARD)
    account, now = view.account, view.ledger.balance
    balance = after(now)
    if fields.way == "correct":
        await AccountService(ctx.session).adjust(account.id, balance, ctx.today)
        return f"account:{account.id}"
    why = _why_not_spending(account, now, balance)
    if why or fields.category_id is None:
        raise DomainError(why or "Choose a category.", code=ProblemCode.INVALID_CARD)
    receipt = await record_expense(
        ctx.session,
        ctx.user,
        ManualExpense(
            description=fields.description,
            spent_on=ctx.today,
            amount=now - balance,
            currency=None,
            category_id=fields.category_id,
        ),
        ctx.rates,
    )
    return f"receipt:{receipt.id}"


class MoneyInArgs(BaseModel):
    """Money put on a card once from outside — a gift, a refund, a top-up."""

    account: str = Field(min_length=1, description="The card or account, by name")
    amount: Amount
    source: str = Field(min_length=1, max_length=120, description="Where it came from")
    received_on: date | None = Field(None, description="YYYY-MM-DD; today when left out")


class MoneyInCard(BaseModel):
    """Money in as the user approves it."""

    account_id: uuid.UUID
    amount: Amount
    source: str = Field(min_length=1, max_length=120)
    received_on: date


class AddMoney(Writer):
    """Money from outside on a card once: income, taxed on a business account (F23.15)."""

    name = "add_money"
    description = "Propose money put on a card once from outside: a gift, a refund, a top-up."
    args = MoneyInArgs
    card_kind = "money_in"
    card = MoneyInCard
    form = (
        FormField("account_id", "account"),
        FormField("amount", "amount"),
        FormField("source", "text"),
        FormField("received_on", "date"),
    )

    async def check(self, ctx: ToolContext, args: MoneyInArgs) -> str | None:
        return (await find_account(ctx, args.account))[1]

    async def propose(self, ctx: ToolContext, args: MoneyInArgs) -> dict[str, Any]:
        account, _ = await find_account(ctx, args.account)
        assert account is not None
        return {
            "account_id": str(account.id),
            "amount": str(args.amount),
            "source": args.source,
            "received_on": (args.received_on or ctx.today).isoformat(),
        }

    async def save(self, ctx: ToolContext, fields: MoneyInCard) -> str:
        income = await AccountService(ctx.session).money_in(
            fields.account_id,
            amount=fields.amount,
            source=fields.source,
            received_on=fields.received_on,
            today=ctx.today,
        )
        return f"income:{income.id}"


class MoveArgs(BaseModel):
    """Money moved once between two of the user's cards."""

    from_account: str = Field(min_length=1, description="The card it leaves, by name")
    to_account: str = Field(min_length=1, description="The card it reaches, by name")
    amount: Amount
    moved_on: date | None = Field(None, description="YYYY-MM-DD; today when left out")


class MoveCard(BaseModel):
    """A move as the user approves it: both cards by their ids."""

    from_account_id: uuid.UUID
    to_account_id: uuid.UUID
    amount: Amount
    moved_on: date


class MoveMoney(Writer):
    """Money moved once between two cards: neither income nor spending (F23.15)."""

    name = "move_money"
    description = "Propose moving a sum once from one of the user's cards to another."
    args = MoveArgs
    card_kind = "move"
    card = MoveCard
    form = (
        FormField("from_account_id", "account"),
        FormField("to_account_id", "account"),
        FormField("amount", "amount"),
        FormField("moved_on", "date"),
    )

    async def check(self, ctx: ToolContext, args: MoveArgs) -> str | None:
        return (await find_account(ctx, args.from_account))[1] or (
            await find_account(ctx, args.to_account)
        )[1]

    async def propose(self, ctx: ToolContext, args: MoveArgs) -> dict[str, Any]:
        source, _ = await find_account(ctx, args.from_account)
        target, _ = await find_account(ctx, args.to_account)
        assert source is not None and target is not None
        return {
            "from_account_id": str(source.id),
            "to_account_id": str(target.id),
            "amount": str(args.amount),
            "moved_on": (args.moved_on or ctx.today).isoformat(),
        }

    async def save(self, ctx: ToolContext, fields: MoveCard) -> str:
        move = await AccountService(ctx.session).move(
            from_id=fields.from_account_id,
            to_id=fields.to_account_id,
            amount=fields.amount,
            moved_on=fields.moved_on,
            today=ctx.today,
        )
        return f"move:{move.id}"
