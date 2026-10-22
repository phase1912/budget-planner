"""Income in words — money that came, regular incomes added, changed or stopped (F21.1,
F21.7, F23.10, F23.17, F23.21). Income lands on a card: with none yet, approving makes
"My card"."""

import json
import uuid
from datetime import date
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.api.errors import NotFoundError
from app.assistant.tools.base import (
    Amount,
    Answer,
    FormField,
    Reader,
    ToolContext,
    Writer,
    as_id,
    find_by_name,
)
from app.domain.income import IncomeKind
from app.models.income_source import IncomeSource
from app.schemas.income import IncomeRequest, IncomeSourceRequest, NewCard
from app.services.income import CARD_NAMES, IncomeService, bill_rule, regular_rule

Day = Field(None, ge=1, le=31, description="Day of the month; 31 is the last")
Weekday = Field(None, ge=0, le=6, description="Weekly on this weekday, 0 Monday … 6 Sunday")


def _new_card(ctx: ToolContext, shared: bool) -> NewCard:
    """The card income lands on when there is none, under its usual name."""
    names = CARD_NAMES[shared]
    return NewCard(name=names.get(ctx.user.language or "en", names["en"]))


class IncomeArgs(BaseModel):
    """Money that came in, as Plan's "Add income" takes it."""

    amount: Amount
    source: str = Field(min_length=1, max_length=80, description="Who paid, e.g. an employer")
    received_on: date | None = Field(None, description="YYYY-MM-DD; today when left out")
    kind: IncomeKind = IncomeKind.SALARY
    shared: bool = Field(False, description="Shared with the family")


class AddIncome(Writer):
    """One sum that came in, on the purchase card or a card made for it."""

    name = "add_income"
    description = "Propose recording money that came in once."
    args = IncomeArgs
    card_kind = "income"
    card = IncomeArgs

    async def propose(self, ctx: ToolContext, args: IncomeArgs) -> dict[str, Any]:
        fields = args.model_dump(mode="json")
        fields["received_on"] = (args.received_on or ctx.today).isoformat()
        return fields

    async def save(self, ctx: ToolContext, fields: IncomeArgs) -> str:
        entry = await IncomeService(ctx.session).add(
            IncomeRequest(
                received_on=fields.received_on or ctx.today,
                amount=fields.amount,
                source=fields.source,
                kind=fields.kind,
                shared=fields.shared,
                new_card=_new_card(ctx, fields.shared),
            )
        )
        return f"income:{entry.id}"


class RemoveIncomeArgs(BaseModel):
    """Which sum that came in, by who paid it and when."""

    source: str = Field(min_length=1, description="Who paid it, as the user says")
    month: str | None = Field(None, pattern=r"^\d{4}-\d{2}$", description="YYYY-MM; this month")


class IncomeRemoval(BaseModel):
    """The entry to remove, as the user approves it."""

    income_id: uuid.UUID
    target: str


class RemoveIncome(Writer):
    """A sum entered by mistake taken out; only this month's can go (F23.15)."""

    name = "remove_income"
    description = "Propose removing a sum that came in this month, found by who paid it."
    args = RemoveIncomeArgs
    card_kind = "income_remove"
    card = IncomeRemoval
    form = (FormField("target", "target"),)

    async def _entry(self, ctx: ToolContext, args: RemoveIncomeArgs) -> tuple[Any, str | None]:
        month = date.fromisoformat(f"{args.month}-01") if args.month else ctx.today.replace(day=1)
        view = await IncomeService(ctx.session).month(ctx.user, month)
        found = find_by_name(view.entries, args.source, lambda e: e.source)
        return found.item, (f"income: {found.error}" if found.error else None)

    async def check(self, ctx: ToolContext, args: RemoveIncomeArgs) -> str | None:
        return (await self._entry(ctx, args))[1]

    async def propose(self, ctx: ToolContext, args: RemoveIncomeArgs) -> dict[str, Any]:
        entry, _ = await self._entry(ctx, args)
        return {
            "income_id": str(entry.id),
            "target": f"{entry.source} · {entry.amount} · {entry.received_on.isoformat()}",
        }

    async def save(self, ctx: ToolContext, fields: IncomeRemoval) -> str:
        await IncomeService(ctx.session).delete(as_id(fields.income_id))
        return f"income:{fields.income_id}"


class RegularArgs(BaseModel):
    """A regular income — a salary, a pension — monthly on a day or weekly."""

    name: str = Field(min_length=1, max_length=80, description="e.g. Salary")
    amount: Amount = Field(description="Each time it comes")
    day: int | None = Day
    weekday: int | None = Weekday
    shared: bool = Field(False, description="Shared with the family")

    @model_validator(mode="after")
    def _weekly_or_monthly(self) -> "RegularArgs":
        if self.weekday is not None:
            self.day = None
        return self


class AddRegularIncome(Writer):
    """A regular income counted from this month, or next when its day has passed."""

    name = "add_regular_income"
    description = "Propose an income that comes every month or every week by itself."
    args = RegularArgs
    card_kind = "regular_income"
    card = RegularArgs
    form = (
        FormField("name", "text"),
        FormField("amount", "amount"),
        FormField("repeat", "repeat"),
        FormField("shared", "switch", required=False),
    )

    async def propose(self, ctx: ToolContext, args: RegularArgs) -> dict[str, Any]:
        return args.model_dump(mode="json")

    async def save(self, ctx: ToolContext, fields: RegularArgs) -> str:
        source = await IncomeService(ctx.session).add_regular(
            IncomeSourceRequest(
                name=fields.name,
                amount=fields.amount,
                day=fields.day,
                weekday=fields.weekday,
                shared=fields.shared,
                new_card=_new_card(ctx, fields.shared),
            ),
            ctx.today,
        )
        return f"regular:{source.id}"


async def _find(ctx: ToolContext, said: str) -> tuple[IncomeSource | None, str | None]:
    found = find_by_name(await IncomeService(ctx.session).regular_incomes(), said, lambda s: s.name)
    return found.item, (f"regular income: {found.error}" if found.error else None)


class ChangeRegularArgs(BaseModel):
    """Which regular income, by its name, and what of it changes."""

    name: str = Field(min_length=1, description="The income as the user calls it")
    new_name: str | None = Field(None, max_length=80)
    amount: Amount | None = None
    day: int | None = Day
    weekday: int | None = Weekday


class RegularChange(BaseModel):
    """A regular income's change as the user approves it."""

    source_id: uuid.UUID
    target: str
    name: str = Field(min_length=1, max_length=80)
    amount: Amount
    day: int | None = Day
    weekday: int | None = Weekday


class ChangeRegularIncome(Writer):
    """A regular income changed from this month on; earlier months keep it (F23.15)."""

    name = "change_regular_income"
    description = "Propose changing a regular income's amount, day or name, found by its name."
    args = ChangeRegularArgs
    card_kind = "regular_income_change"
    card = RegularChange
    form = (
        FormField("target", "target"),
        FormField("name", "text"),
        FormField("amount", "amount"),
        FormField("repeat", "repeat"),
    )

    async def check(self, ctx: ToolContext, args: ChangeRegularArgs) -> str | None:
        return (await _find(ctx, args.name))[1]

    async def propose(self, ctx: ToolContext, args: ChangeRegularArgs) -> dict[str, Any]:
        source, _ = await _find(ctx, args.name)
        assert source is not None
        weekly, monthly = args.weekday, args.day
        return {
            "source_id": str(source.id),
            "target": source.name,
            "name": args.new_name or source.name,
            "amount": str(args.amount or source.amount),
            "day": None if weekly is not None else (monthly or source.day),
            "weekday": weekly if weekly is not None else (None if monthly else source.weekday),
        }

    async def save(self, ctx: ToolContext, fields: RegularChange) -> str:
        incomes = IncomeService(ctx.session)
        source = next(
            (s for s in await incomes.regular_incomes() if s.id == fields.source_id), None
        )
        if source is None:
            raise NotFoundError("No such regular income.")
        changed = await incomes.change_regular(
            source.id,
            IncomeSourceRequest(
                name=fields.name,
                amount=fields.amount,
                day=fields.day,
                weekday=fields.weekday,
                taxed=source.taxed,
                shared=source.household_id is not None,
                account_id=source.account_id,
                about=source.about,
            ),
        )
        return f"regular:{changed.id}"


class StopRegularArgs(BaseModel):
    """Which regular income to stop, by its name."""

    name: str = Field(min_length=1, description="The income as the user calls it")


class RegularStop(BaseModel):
    """The regular income to stop, as the user approves it."""

    source_id: uuid.UUID
    target: str


class StopRegularIncome(Writer):
    """A regular income stopped from next month; this month and the past keep it."""

    name = "stop_regular_income"
    description = "Propose stopping a regular income from next month, found by its name."
    args = StopRegularArgs
    card_kind = "regular_income_stop"
    card = RegularStop
    form = (FormField("target", "target"),)

    async def check(self, ctx: ToolContext, args: StopRegularArgs) -> str | None:
        return (await _find(ctx, args.name))[1]

    async def propose(self, ctx: ToolContext, args: StopRegularArgs) -> dict[str, Any]:
        source, _ = await _find(ctx, args.name)
        assert source is not None
        return {"source_id": str(source.id), "target": source.name}

    async def save(self, ctx: ToolContext, fields: RegularStop) -> str:
        await IncomeService(ctx.session).end_regular(as_id(fields.source_id), ctx.today)
        return f"regular:{fields.source_id}"


class NoArgs(BaseModel):
    """Nothing to say beyond the wish itself."""


class RegularMoney(Reader):
    """The regular incomes and bills running, each with what it comes to this month."""

    name = "regular_money"
    description = "The user's regular incomes and bills: names, amounts, when they come."
    args = NoArgs

    async def read(self, ctx: ToolContext, args: NoArgs) -> Answer:
        incomes = IncomeService(ctx.session)
        month = ctx.today.replace(day=1)

        def row(name: str, amount: Any, day: Any, weekday: Any, this_month: Any) -> dict[str, Any]:
            return {
                "name": name,
                "amount": str(amount),
                "day": day,
                "weekday": weekday,
                "this_month": str(this_month),
            }

        return Answer(
            json.dumps(
                {
                    "currency": ctx.user.currency,
                    "incomes": [
                        row(s.name, s.amount, s.day, s.weekday, regular_rule(s).in_month(month))
                        for s in await incomes.regular_incomes()
                    ],
                    "bills": [
                        row(b.name, b.amount, b.day, b.weekday, bill_rule(b).in_month(month))
                        for b in await incomes.regular_bills()
                    ],
                }
            )
        )
