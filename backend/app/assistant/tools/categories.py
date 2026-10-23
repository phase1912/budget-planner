"""A receipt's lines and their categories, and filing them elsewhere, by chat (F21.15)."""

import json
import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.api.errors import NotFoundError
from app.assistant.tools.base import Answer, FormField, Reader, ToolContext, Writer, as_id
from app.domain.categories import UNCATEGORIZED
from app.models.category import Category
from app.models.receipt import Receipt
from app.repository.category import CategoryRepository
from app.repository.receipt import ReceiptRepository
from app.services.categorisation import CategorisationService
from app.services.taxonomy import TaxonomyService


class NoArgs(BaseModel):
    """Nothing to say: the tool reads the user's whole list."""


class ReceiptRef(BaseModel):
    """One of the user's receipts, by the id the receipts tool gave it."""

    receipt_id: str = Field(description="The `id` the receipts tool gave the receipt")


def _receipt_id(said: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(said.strip())
    except ValueError:
        return None


async def _own_receipt(ctx: ToolContext, said: str) -> Receipt | None:
    """The user's own receipt with its lines; another member's is not theirs to refile (N2)."""
    receipt_id = _receipt_id(said)
    if receipt_id is None:
        return None
    return await ReceiptRepository(ctx.session).get_with_items(receipt_id)


def _label(receipt: Receipt) -> str:
    day = receipt.transaction_date.date().isoformat() if receipt.transaction_date else ""
    total = str(receipt.total_amount) if receipt.total_amount is not None else ""
    return " · ".join(p for p in (receipt.merchant_name or "", day, total) if p)


class Categories(Reader):
    """The categories the user can file under: the built-in ones and their own (C1, C6)."""

    name = "categories"
    description = "The categories the user's purchases can be filed under."
    args = NoArgs

    async def read(self, ctx: ToolContext, args: NoArgs) -> Answer:
        categories = await ctx.categories()
        return Answer(
            json.dumps(
                {
                    "categories": [
                        {"name": c.name, "own": c.user_id is not None}
                        for c in categories
                        if c.name != UNCATEGORIZED
                    ]
                }
            )
        )


class ReceiptLines(Reader):
    """One receipt's lines, each with its category, for "which category was it?" (C3)."""

    name = "receipt_lines"
    description = "One of the user's receipts, line by line, with the category of each line."
    args = ReceiptRef

    async def read(self, ctx: ToolContext, args: ReceiptRef) -> Answer:
        receipt = await _own_receipt(ctx, args.receipt_id)
        if receipt is None:
            return Answer(json.dumps({"error": "no receipt of the user's with that id"}))
        return Answer(
            json.dumps(
                {
                    "id": str(receipt.id),
                    "shop": receipt.merchant_name,
                    "total": str(receipt.total_amount) if receipt.total_amount else None,
                    "currency": ctx.user.currency,
                    "lines": [
                        {
                            "name": line.name,
                            "total": str(line.total_price),
                            "category": line.category.name if line.category else UNCATEGORIZED,
                        }
                        for line in sorted(receipt.line_items, key=lambda i: i.position)
                    ],
                }
            )
        )


class CategoryArgs(BaseModel):
    """A new category of the user's own."""

    name: str = Field(min_length=1, max_length=100, description="The category's name")


class CategoryCard(BaseModel):
    """A new category as the user approves it."""

    name: str = Field(min_length=1, max_length=100)


class AddCategory(Writer):
    """A new category card, made as on the Categories screen (C6)."""

    name = "add_category"
    description = (
        "Propose a new category of the user's own. To file a receipt under a new category, "
        "call move_to_category only: approving it makes the category too."
    )
    args = CategoryArgs
    card_kind = "category"
    card = CategoryCard
    form = (FormField("name", "text"),)

    async def check(self, ctx: ToolContext, args: CategoryArgs) -> str | None:
        if _named(await ctx.categories(), args.name) is not None:
            return f"the user already has a category named {args.name!r}"
        return None

    async def propose(self, ctx: ToolContext, args: CategoryArgs) -> dict[str, Any]:
        return {"name": args.name.strip()}

    async def save(self, ctx: ToolContext, fields: CategoryCard) -> str:
        # A move card approved first may have made it already: then there is nothing to add.
        category = _named(await ctx.categories(), fields.name) or await TaxonomyService(
            CategoryRepository(ctx.session)
        ).create(ctx.user.id, fields.name.strip())
        return f"category:{category.id}"


def _named(categories: list[Category], name: str) -> Category | None:
    wanted = name.strip().lower()
    return next((c for c in categories if c.name.lower() == wanted), None)


class MoveArgs(BaseModel):
    """A receipt, or one of its lines, to file under a category — new or the user's own."""

    receipt_id: str = Field(description="The `id` the receipts tool gave the receipt")
    category: str = Field(min_length=1, max_length=100, description="The category, by name")
    line: str | None = Field(
        None, max_length=120, description="Only this line of the receipt; the whole by default"
    )


class MoveCard(BaseModel):
    """A move as the user approves it: which lines, and the category by its name."""

    target: str
    receipt_id: uuid.UUID
    line_ids: list[uuid.UUID]
    category: str = Field(min_length=1, max_length=100)


class MoveToCategory(Writer):
    """A card filing a receipt, or one line of it, under a category (C4, C6).

    The category is kept by name, so a move into a category that does not exist yet makes it
    when approved — one card for "create Subscriptions and put it there". Each line is
    refiled as the user's own correction, which the categoriser learns from (C4, C5).
    """

    name = "move_to_category"
    description = (
        "Propose filing one of the user's receipts, or one line of it, under a category; "
        "a category the user does not have yet is made when the card is approved."
    )
    args = MoveArgs
    card_kind = "category_move"
    card = MoveCard
    form = (FormField("target", "target"), FormField("category", "text"))

    async def check(self, ctx: ToolContext, args: MoveArgs) -> str | None:
        receipt = await _own_receipt(ctx, args.receipt_id)
        if receipt is None:
            return (
                "no receipt of the user's own with that id; another family member's receipt "
                "is theirs to refile"
            )
        if args.line and not _lines(receipt, args.line):
            names = ", ".join(i.name for i in receipt.line_items)
            return f"no line named {args.line!r} on that receipt; it has: {names}"
        return None

    async def propose(self, ctx: ToolContext, args: MoveArgs) -> dict[str, Any]:
        receipt = await _own_receipt(ctx, args.receipt_id)
        if receipt is None:
            raise NotFoundError("No such receipt.")
        lines = _lines(receipt, args.line) if args.line else list(receipt.line_items)
        own = _named(await ctx.categories(), args.category)
        target = _label(receipt)
        if args.line:
            target = f"{', '.join(i.name for i in lines)} — {target}"
        return {
            "target": target,
            "receipt_id": str(receipt.id),
            "line_ids": [str(i.id) for i in lines],
            "category": own.name if own else args.category.strip(),
        }

    async def save(self, ctx: ToolContext, fields: MoveCard) -> str:
        categories = CategoryRepository(ctx.session)
        category = _named(await ctx.categories(), fields.category) or await TaxonomyService(
            categories
        ).create(ctx.user.id, fields.category.strip())
        service = CategorisationService(ReceiptRepository(ctx.session), categories)
        for line_id in fields.line_ids:
            await service.reassign(as_id(line_id), category.id, ctx.user.id, apply_to_future=True)
        return f"receipt:{fields.receipt_id}"


def _lines(receipt: Receipt, said: str) -> list[Any]:
    wanted = said.strip().lower()
    exact = [i for i in receipt.line_items if i.name.lower() == wanted]
    return exact or [i for i in receipt.line_items if wanted in i.name.lower()]
