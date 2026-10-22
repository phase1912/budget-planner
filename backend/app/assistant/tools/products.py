"""Products in words (F21.6, F21.13): finding what was bought, and saving products as a group
the Products screen explores together (F16.2).

Products are named as the receipts print them, mostly in the shop's language, so a search
takes several spellings at once — "milk", "mleko", "молоко" — and keeps what any finds.
"""

import json
import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.assistant.tools.base import Answer, FormField, Reader, ToolContext, Writer, as_id
from app.services.product import ProductService, ProductSummary

FOUND = 12
"""Products named in one answer."""


async def _search(ctx: ToolContext, words: list[str]) -> list[ProductSummary]:
    """The user's products any of `words` finds, most bought first, each once."""
    products = ProductService(ctx.session)
    seen: dict[uuid.UUID, ProductSummary] = {}
    for word in words:
        for p in await products.list_products(ctx.user.id, word):
            seen.setdefault(p.id, p)
    return sorted(seen.values(), key=lambda p: (-p.purchases, p.name))


class FindArgs(BaseModel):
    """What to look for, in every spelling it may be printed in."""

    words: list[str] = Field(
        min_length=1,
        max_length=6,
        description=(
            "What the product is called, in the user's words and as receipts print it in "
            "the shop's language, e.g. ['milk', 'mleko', 'молоко']"
        ),
    )


class FindProducts(Reader):
    """Products the user bought matching any of the words, with how often and what they
    cost; the answer card opens them together on the Products screen."""

    name = "find_products"
    description = (
        "Find products the user bought: names as printed, times bought, money spent. Use it "
        "to show products, or to get the exact names before grouping them."
    )
    args = FindArgs

    async def read(self, ctx: ToolContext, args: FindArgs) -> Answer:
        found = (await _search(ctx, args.words))[:FOUND]
        figures = {
            "currency": ctx.user.currency,
            "products": [
                {"name": p.name, "times_bought": p.purchases, "spent": str(p.spent)} for p in found
            ],
        }
        card = (
            {
                "screen": "products",
                "to": "/products/explore?products=" + ",".join(str(p.id) for p in found),
            }
            if found
            else None
        )
        return Answer(json.dumps(figures, ensure_ascii=False), card)


class GroupArgs(BaseModel):
    """Products to keep together under a name."""

    name: str = Field(min_length=1, max_length=60, description="The group's name, e.g. Snacks")
    products: list[str] = Field(
        min_length=1,
        max_length=30,
        description="Exact product names as find_products returned them",
    )


class GroupCard(BaseModel):
    """A product group as the user approves it: the products by their ids."""

    name: str = Field(min_length=1, max_length=60)
    product_ids: list[uuid.UUID] = Field(min_length=1)
    products: list[str] = []


class SaveProductGroup(Writer):
    """Products saved together under a name, to explore and compare on the Products
    screen (F16.2)."""

    name = "save_product_group"
    description = (
        "Propose saving products as a named group. Call find_products first and pass the "
        "exact names it returned."
    )
    args = GroupArgs
    card_kind = "product_group"
    card = GroupCard
    form = (FormField("name", "text"), FormField("products", "items"))

    async def _found(
        self, ctx: ToolContext, args: GroupArgs
    ) -> tuple[list[ProductSummary], list[str]]:
        mine = {p.name.lower(): p for p in await _search(ctx, [""])}
        found = [mine[n.strip().lower()] for n in args.products if n.strip().lower() in mine]
        missing = [n for n in args.products if n.strip().lower() not in mine]
        return found, missing

    async def check(self, ctx: ToolContext, args: GroupArgs) -> str | None:
        _, missing = await self._found(ctx, args)
        if missing:
            return f"no products named {missing}: call find_products and use its exact names"
        return None

    async def propose(self, ctx: ToolContext, args: GroupArgs) -> dict[str, Any]:
        found, _ = await self._found(ctx, args)
        unique = list({p.id: p for p in found}.values())
        return {
            "name": args.name,
            "product_ids": [str(p.id) for p in unique],
            "products": [p.name for p in unique],
        }

    async def save(self, ctx: ToolContext, fields: GroupCard) -> str:
        group = await ProductService(ctx.session).save_selection(
            ctx.user.id, fields.name, [as_id(p) for p in fields.product_ids]
        )
        return f"product_group:{group.id}"
