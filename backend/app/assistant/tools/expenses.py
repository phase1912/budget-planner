"""Money spent without a receipt, said in words (F21.3)."""

import uuid
from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from app.assistant.tools.base import Amount, ToolContext, Writer
from app.services.manual_expense import ManualExpense, record_expense

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
