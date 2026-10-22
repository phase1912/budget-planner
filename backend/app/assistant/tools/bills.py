"""Regular bills — rent, a subscription, the gym — added, changed or stopped in words
(F21.1, F21.7, F23.18, F23.21)."""

import uuid
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.api.errors import NotFoundError
from app.assistant.tools.base import Amount, FormField, ToolContext, Writer, as_id, find_by_name
from app.models.regular_expense import RegularExpense
from app.schemas.income import RegularExpenseRequest
from app.services.income import IncomeService

Day = Field(None, ge=1, le=31, description="Day of the month; 31 is the last")
Weekday = Field(None, ge=0, le=6, description="Weekly on this weekday, 0 Monday … 6 Sunday")


class BillArgs(BaseModel):
    """A bill that goes by itself, monthly or weekly, as Plan's regular bills take it."""

    name: str = Field(min_length=1, max_length=80)
    amount: Amount = Field(description="Each time it goes")
    day: int | None = Day
    weekday: int | None = Weekday
    shared: bool = Field(False, description="Shared with the family")

    @model_validator(mode="after")
    def _weekly_or_monthly(self) -> "BillArgs":
        if self.weekday is not None:
            self.day = None
        return self


class AddBill(Writer):
    """A new bill, counting from this month in the budget and on the purchase card."""

    name = "add_bill"
    description = "Propose a bill that goes every month or every week by itself."
    args = BillArgs
    card_kind = "bill"
    card = BillArgs

    async def propose(self, ctx: ToolContext, args: BillArgs) -> dict[str, Any]:
        return args.model_dump(mode="json")

    async def save(self, ctx: ToolContext, fields: BillArgs) -> str:
        bill = await IncomeService(ctx.session).add_bill(
            RegularExpenseRequest(
                name=fields.name,
                amount=fields.amount,
                day=fields.day,
                weekday=fields.weekday,
                shared=fields.shared,
            ),
            ctx.today,
        )
        return f"bill:{bill.id}"


async def _find(ctx: ToolContext, said: str) -> tuple[RegularExpense | None, str | None]:
    found = find_by_name(await IncomeService(ctx.session).regular_bills(), said, lambda b: b.name)
    return found.item, (f"bill: {found.error}" if found.error else None)


class ChangeArgs(BaseModel):
    """Which bill, by the name the user gave it, and what of it changes."""

    name: str = Field(min_length=1, description="The bill as the user calls it")
    new_name: str | None = Field(None, max_length=80)
    amount: Amount | None = None
    day: int | None = Day
    weekday: int | None = Weekday


class BillChange(BaseModel):
    """A bill's change as the user approves it: every field as it will be."""

    bill_id: uuid.UUID
    target: str
    name: str = Field(min_length=1, max_length=80)
    amount: Amount
    day: int | None = Day
    weekday: int | None = Weekday


class ChangeBill(Writer):
    """A bill changed from this month on; earlier months keep what it was (F23.15)."""

    name = "change_bill"
    description = "Propose changing a regular bill's amount, day or name, found by its name."
    args = ChangeArgs
    card_kind = "bill_change"
    card = BillChange
    form = (
        FormField("target", "target"),
        FormField("name", "text"),
        FormField("amount", "amount"),
        FormField("repeat", "repeat"),
    )

    async def check(self, ctx: ToolContext, args: ChangeArgs) -> str | None:
        return (await _find(ctx, args.name))[1]

    async def propose(self, ctx: ToolContext, args: ChangeArgs) -> dict[str, Any]:
        bill, _ = await _find(ctx, args.name)
        assert bill is not None
        weekly = args.weekday if args.weekday is not None else None
        monthly = args.day if args.day is not None else None
        return {
            "bill_id": str(bill.id),
            "target": bill.name,
            "name": args.new_name or bill.name,
            "amount": str(args.amount or bill.amount),
            "day": None if weekly is not None else (monthly or bill.day),
            "weekday": weekly if weekly is not None else (None if monthly else bill.weekday),
        }

    async def save(self, ctx: ToolContext, fields: BillChange) -> str:
        incomes = IncomeService(ctx.session)
        bill = next((b for b in await incomes.regular_bills() if b.id == fields.bill_id), None)
        if bill is None:
            raise NotFoundError("No such regular bill.")
        changed = await incomes.change_bill(
            bill.id,
            RegularExpenseRequest(
                name=fields.name,
                amount=fields.amount,
                day=fields.day,
                weekday=fields.weekday,
                shared=bill.household_id is not None,
                account_id=bill.account_id,
            ),
        )
        return f"bill:{changed.id}"


class StopArgs(BaseModel):
    """Which bill to stop, by the name the user gave it."""

    name: str = Field(min_length=1, description="The bill as the user calls it")


class BillStop(BaseModel):
    """The bill to stop, as the user approves it."""

    bill_id: uuid.UUID
    target: str


class StopBill(Writer):
    """A bill stopped from next month; this month and the past keep it, as on Plan."""

    name = "stop_bill"
    description = "Propose stopping a regular bill from next month, found by its name."
    args = StopArgs
    card_kind = "bill_stop"
    card = BillStop
    form = (FormField("target", "target"),)

    async def check(self, ctx: ToolContext, args: StopArgs) -> str | None:
        return (await _find(ctx, args.name))[1]

    async def propose(self, ctx: ToolContext, args: StopArgs) -> dict[str, Any]:
        bill, _ = await _find(ctx, args.name)
        assert bill is not None
        return {"bill_id": str(bill.id), "target": bill.name}

    async def save(self, ctx: ToolContext, fields: BillStop) -> str:
        await IncomeService(ctx.session).end_bill(as_id(fields.bill_id), ctx.today)
        return f"bill:{fields.bill_id}"
