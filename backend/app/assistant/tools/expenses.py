"""Money spent without a receipt, said in words (F21.3)."""

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.assistant.tools.base import Amount, FormField, ToolContext, Writer
from app.services.manual_expense import (
    ManualExpense,
    ToldLine,
    ToldReceipt,
    record_expense,
    record_told_receipt,
)

FALLBACK_CATEGORIES = ("Other", "Uncategorized")
"""Where an expense goes when the model named no category the user has."""


class ExpenseArgs(BaseModel):
    """Money spent without a receipt — a taxi, a coffee — as the model understood it."""

    description: str = Field(min_length=1, max_length=255, description="What it was")
    amount: Amount
    spent_on: date | None = Field(None, description="YYYY-MM-DD; today when left out")
    category: str | None = Field(None, description="One of the user's categories, by name")
    currency: str | None = Field(None, pattern=r"^[A-Z]{3}$", description="Only if not theirs")


class ExpenseCard(BaseModel):
    """An expense card as the user approves it: the category by its id (F20.5)."""

    description: str = Field(min_length=1, max_length=255)
    amount: Amount
    spent_on: date
    category_id: uuid.UUID
    currency: str | None = Field(None, pattern=r"^[A-Z]{3}$")


class AddExpense(Writer):
    """An expense card: the day resolved, the category matched by name to the user's own,
    else the closest catch-all, so it opens ready to approve; saved as a manual receipt."""

    name = "add_expense"
    description = "Propose money spent without a receipt — one call per thing bought."
    args = ExpenseArgs
    card_kind = "expense"
    card = ExpenseCard

    async def propose(self, ctx: ToolContext, args: ExpenseArgs) -> dict[str, Any]:
        categories = await ctx.categories()
        wanted = (args.category or "").strip().lower()
        chosen = next((c for c in categories if c.name.lower() == wanted), None) or next(
            (c for c in categories if c.name in FALLBACK_CATEGORIES), None
        )
        return {
            "description": args.description,
            "amount": str(args.amount),
            "spent_on": (args.spent_on or ctx.today).isoformat(),
            "currency": args.currency,
            "category_id": str(chosen.id) if chosen else None,
        }

    async def save(self, ctx: ToolContext, fields: ExpenseCard) -> str:
        receipt = await record_expense(
            ctx.session,
            ctx.user,
            ManualExpense(
                description=fields.description,
                spent_on=fields.spent_on,
                amount=fields.amount,
                currency=fields.currency,
                category_id=fields.category_id,
            ),
            ctx.rates,
        )
        return f"receipt:{receipt.id}"


class ToldLineArgs(BaseModel):
    """One thing bought, as the user said it."""

    name: str = Field(min_length=1, max_length=255, description="What it was")
    quantity: Decimal = Field(Decimal(1), gt=0, description="How many; 1 when not said")
    amount: Amount = Field(description="What it cost in all")


class ToldReceiptArgs(BaseModel):
    """A shopping trip told line by line — "Biedronka today: milk 4, bread 5"."""

    shop: str = Field(min_length=1, max_length=255, description="The shop")
    spent_on: date | None = Field(None, description="YYYY-MM-DD; today when left out")
    lines: list[ToldLineArgs] = Field(min_length=1, max_length=100)
    currency: str | None = Field(None, pattern=r"^[A-Z]{3}$", description="Only if not theirs")


class ToldReceiptCard(BaseModel):
    """A told receipt as the user approves it, its lines edited or taken out."""

    shop: str = Field(min_length=1, max_length=255)
    spent_on: date
    lines: list[ToldLineArgs] = Field(min_length=1, max_length=100)
    currency: str | None = Field(None, pattern=r"^[A-Z]{3}$")


class AddToldReceipt(Writer):
    """A receipt card from a shopping trip told in words (F21.8.1): one card with every line,
    stored as a receipt of that shop — no photo, marked as told — its lines categorised as a
    read receipt's are once approved, so it counts like any receipt in the month, Spending
    and Products."""

    name = "add_told_receipt"
    description = (
        "Propose a receipt the user tells line by line — a shop, a day and what was bought "
        "there with prices — as one card. Only for purchases told with their prices: names "
        "without prices are products to look up (find_products). For one thing with no "
        "shop, use add_expense."
    )
    args = ToldReceiptArgs
    card_kind = "told_receipt"
    card = ToldReceiptCard
    form = (
        FormField("shop", "text"),
        FormField("spent_on", "date"),
        FormField("lines", "lines"),
    )

    async def propose(self, ctx: ToolContext, args: ToldReceiptArgs) -> dict[str, Any]:
        return {
            "shop": args.shop.strip(),
            "spent_on": (args.spent_on or ctx.today).isoformat(),
            "currency": args.currency,
            "lines": [
                {
                    "name": line.name.strip(),
                    "quantity": str(line.quantity),
                    "amount": str(line.amount),
                }
                for line in args.lines
            ],
        }

    async def save(self, ctx: ToolContext, fields: ToldReceiptCard) -> str:
        receipt = await record_told_receipt(
            ctx.session,
            ctx.user,
            ToldReceipt(
                shop=fields.shop,
                spent_on=fields.spent_on,
                lines=[ToldLine(line.name, line.quantity, line.amount) for line in fields.lines],
                currency=fields.currency,
            ),
            ctx.rates,
            ctx.categoriser,
        )
        return f"receipt:{receipt.id}"
