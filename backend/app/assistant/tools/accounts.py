"""Accounts in words — cards opened, changed or removed, monthly transfers between them,
and what is on them (F21.7, F23.15, F23.21). The rules of the Accounts screen hold: a
business account sets its tax aside, the last card removed goes back to a budget alone."""

import json
import uuid
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.assistant.core.ports import Intent
from app.assistant.tools.base import (
    Amount,
    Answer,
    Balance,
    FormField,
    Reader,
    ToolContext,
    Writer,
    as_id,
    find_by_name,
)
from app.domain.accounts import AccountKind
from app.models.account import Account, RegularTransfer
from app.repository.money_accounts import AccountRepository
from app.services.money_accounts import AccountService

Kind = Literal["personal", "business", "deposit"]
KINDS: tuple[str, ...] = ("personal", "business", "deposit")


async def _find(ctx: ToolContext, said: str) -> tuple[Account | None, str | None]:
    found = find_by_name(
        list(await AccountRepository(ctx.session).visible()), said, lambda a: a.name
    )
    return found.item, (f"account: {found.error}" if found.error else None)


class AccountArgs(BaseModel):
    """A card or account as the user describes it."""

    name: str = Field(min_length=1, max_length=80)
    kind: Kind = Field("personal", description="personal card, business account or deposit")
    balance: Balance = Field(Decimal("0.00"), description="What is on it now")
    tax_rate: Amount | None = Field(None, description="Business only: tax set aside, %")
    shared: bool = Field(False, description="Shared with the family")


class AddAccount(Writer):
    """A new account opened today with what is on it now."""

    name = "add_account"
    description = "Propose a new card, business account or deposit."
    args = AccountArgs
    intents = frozenset({Intent.ADD})
    card_kind = "account"
    card = AccountArgs
    form = (
        FormField("name", "text"),
        FormField("kind", "choice", options=KINDS),
        FormField("balance", "balance"),
        FormField("tax_rate", "percent", required=False),
        FormField("shared", "switch", required=False),
    )

    async def propose(self, ctx: ToolContext, args: AccountArgs) -> dict[str, Any]:
        return args.model_dump(mode="json")

    async def save(self, ctx: ToolContext, fields: AccountArgs) -> str:
        account = await AccountService(ctx.session).create(
            name=fields.name,
            kind=AccountKind(fields.kind),
            opening=fields.balance,
            opening_on=ctx.today,
            tax_rate=fields.tax_rate,
            shared=fields.shared,
            for_purchases=False,
        )
        return f"account:{account.id}"


class RemoveAccountArgs(BaseModel):
    """Which account to remove, by its name."""

    name: str = Field(min_length=1, description="The account as the user calls it")


class AccountRemoval(BaseModel):
    """The account to remove, as the user approves it."""

    account_id: uuid.UUID
    target: str


class RemoveAccount(Writer):
    """An account removed with the transfers on it; the last one goes back to a budget
    alone (F23.21)."""

    name = "remove_account"
    description = "Propose removing a card or account, found by its name."
    args = RemoveAccountArgs
    intents = frozenset({Intent.REMOVE})
    card_kind = "account_remove"
    card = AccountRemoval
    form = (FormField("target", "target"),)

    async def check(self, ctx: ToolContext, args: RemoveAccountArgs) -> str | None:
        return (await _find(ctx, args.name))[1]

    async def propose(self, ctx: ToolContext, args: RemoveAccountArgs) -> dict[str, Any]:
        account, _ = await _find(ctx, args.name)
        assert account is not None
        return {"account_id": str(account.id), "target": account.name}

    async def save(self, ctx: ToolContext, fields: AccountRemoval) -> str:
        await AccountService(ctx.session).remove(as_id(fields.account_id), ctx.today)
        return f"account:{fields.account_id}"


class TransferArgs(BaseModel):
    """Money moved every month between two of the user's accounts."""

    from_account: str = Field(min_length=1, description="The account it leaves, by name")
    to_account: str = Field(min_length=1, description="The account it reaches, by name")
    amount: Amount
    day: int | None = Field(None, ge=1, le=31, description="Day of the month; 31 is the last")


class TransferCard(BaseModel):
    """A monthly transfer as the user approves it: both accounts by their ids."""

    from_account_id: uuid.UUID
    to_account_id: uuid.UUID
    amount: Amount
    day: int | None = Field(None, ge=1, le=31)


class AddTransfer(Writer):
    """A monthly transfer, from the first day still to come (F23.15)."""

    name = "add_transfer"
    description = "Propose moving money every month from one of the user's accounts to another."
    args = TransferArgs
    intents = frozenset({Intent.ADD})
    card_kind = "transfer"
    card = TransferCard
    form = (
        FormField("from_account_id", "account"),
        FormField("to_account_id", "account"),
        FormField("amount", "amount"),
        FormField("day", "day", required=False),
    )

    async def check(self, ctx: ToolContext, args: TransferArgs) -> str | None:
        return (await _find(ctx, args.from_account))[1] or (await _find(ctx, args.to_account))[1]

    async def propose(self, ctx: ToolContext, args: TransferArgs) -> dict[str, Any]:
        source, _ = await _find(ctx, args.from_account)
        target, _ = await _find(ctx, args.to_account)
        assert source is not None and target is not None
        return {
            "from_account_id": str(source.id),
            "to_account_id": str(target.id),
            "amount": str(args.amount),
            "day": args.day,
        }

    async def save(self, ctx: ToolContext, fields: TransferCard) -> str:
        rule = await AccountService(ctx.session).add_transfer_rule(
            from_id=fields.from_account_id,
            to_id=fields.to_account_id,
            amount=fields.amount,
            day=fields.day,
            today=ctx.today,
            name=None,
        )
        return f"transfer:{rule.id}"


async def _transfer(ctx: ToolContext, said: str) -> tuple[RegularTransfer | None, str | None]:
    found = find_by_name(await AccountService(ctx.session).transfer_rules(), said, lambda r: r.name)
    return found.item, (f"transfer: {found.error}" if found.error else None)


class StopTransferArgs(BaseModel):
    """Which monthly transfer to stop, by its name or the account it goes to."""

    name: str = Field(min_length=1, description="The transfer as the user calls it")


class TransferStop(BaseModel):
    """The transfer to stop, as the user approves it."""

    rule_id: uuid.UUID
    target: str


class StopTransfer(Writer):
    """A monthly transfer stopped from next month; one started this month simply goes."""

    name = "stop_transfer"
    description = "Propose stopping a monthly transfer from next month, found by its name."
    args = StopTransferArgs
    intents = frozenset({Intent.REMOVE})
    card_kind = "transfer_stop"
    card = TransferStop
    form = (FormField("target", "target"),)

    async def check(self, ctx: ToolContext, args: StopTransferArgs) -> str | None:
        return (await _transfer(ctx, args.name))[1]

    async def propose(self, ctx: ToolContext, args: StopTransferArgs) -> dict[str, Any]:
        rule, _ = await _transfer(ctx, args.name)
        assert rule is not None
        return {"rule_id": str(rule.id), "target": rule.name}

    async def save(self, ctx: ToolContext, fields: TransferStop) -> str:
        await AccountService(ctx.session).end_transfer_rule(as_id(fields.rule_id), ctx.today)
        return f"transfer:{fields.rule_id}"


class NoArgs(BaseModel):
    """Nothing to say beyond the wish itself."""


class Accounts(Reader):
    """What is on each account the user sees, now."""

    name = "accounts"
    description = "The user's cards and accounts and what is on each now."
    args = NoArgs

    async def read(self, ctx: ToolContext, args: NoArgs) -> Answer:
        overview = await AccountService(ctx.session).overview(ctx.today)
        return Answer(
            json.dumps(
                {
                    "currency": ctx.user.currency,
                    "total": str(overview.total),
                    "accounts": [
                        {
                            "name": a.account.name,
                            "kind": str(a.account.kind),
                            "balance": str(a.ledger.balance),
                        }
                        for a in overview.accounts
                    ],
                }
            ),
            {"screen": "accounts", "to": "/accounts"} if overview.accounts else None,
        )
