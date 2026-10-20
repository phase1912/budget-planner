"""Questions about spending, answered from the screens' own queries (F21.4, ADR-0025).

Each read tool returns the figures as JSON the model words the answer from, and an
answer card the conversation shows below it: the chart the Spending screen would draw,
or a link to the screen that holds the full list with the same filters. Only the
caller's data is read — the repositories filter by the signed-in user (N2).
"""

import json
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import urlencode

from pydantic import BaseModel, Field

from app.domain.budget import BudgetMonth
from app.domain.categories import ItemView
from app.domain.periods import DateRange
from app.models.user import User
from app.repository.receipt import ReceiptRepository
from app.services.product import ProductService
from app.services.statistics import StatisticsService, statistics_response

LISTED = 8
"""Receipts and products named in one answer: enough to answer, few enough to read."""


class PeriodArgs(BaseModel):
    """A period: a month, or a run of days; this month when neither is given."""

    month: str | None = Field(None, pattern=r"^\d{4}-\d{2}$", description="YYYY-MM")
    start: date | None = Field(None, description="YYYY-MM-DD, first day included")
    end: date | None = Field(None, description="YYYY-MM-DD, last day included")

    def period(self, today: date) -> DateRange:
        """The days asked about. Raises ValueError for a period that ends before it starts."""
        if self.start or self.end:
            return DateRange(self.start or self.end or today, self.end or today)
        if self.month:
            year, month = (int(part) for part in self.month.split("-"))
            return DateRange.of_month(BudgetMonth(year, month))
        return DateRange.of_month(BudgetMonth(today.year, today.month))


class CategoryArgs(PeriodArgs):
    """Spending by category, optionally against the period just before."""

    compare: bool = Field(False, description="Also the period before, like for like")


class ReceiptArgs(PeriodArgs):
    """Receipts from a shop, or holding an item, over a period."""

    shop: str | None = Field(None, max_length=80, description="Part of the shop's name")
    item: str | None = Field(None, max_length=80, description="Part of an item's name")


class ProductArgs(BaseModel):
    """A product's prices and shops; all time unless a period is given."""

    name: str = Field(min_length=1, max_length=80, description="The product, as the user says")
    start: date | None = Field(None, description="YYYY-MM-DD")
    end: date | None = Field(None, description="YYYY-MM-DD")


@dataclass(frozen=True)
class Answer:
    """What a read tool found: the figures for the model, the card for the user."""

    figures: str
    card: dict[str, Any] | None = None


def _link(path: str, **query: str | None) -> str:
    kept = {k: v for k, v in query.items() if v}
    return f"{path}?{urlencode(kept)}" if kept else path


class SpendingReads:
    """The read tools of F21.4, bound to the signed-in user for one request."""

    def __init__(self, session: Any, user: User, today: date) -> None:
        self.session = session
        self.user = user
        self.today = today

    async def by_category(self, args: CategoryArgs) -> Answer:
        """The period's spend per category, as the Spending screen counts it (BRD E1-E6)."""
        period = args.period(self.today)
        stats = statistics_response(
            await StatisticsService(ReceiptRepository(self.session)).category_statistics(
                period, compare=args.compare, chart=True
            )
        )
        previous = stats.comparison
        figures = {
            "start": period.start.isoformat(),
            "end": period.end.isoformat(),
            "currency": self.user.currency,
            "receipts": stats.receipt_count,
            "spent": str(stats.total) if stats.total is not None else None,
            "categories": [
                {
                    "name": c.name or "Uncategorized",
                    "spent": str(c.total),
                    **({"before": str(c.previous_total)} if c.previous_total is not None else {}),
                }
                for c in stats.categories[:10]
            ],
        }
        if previous:
            figures["before"] = {
                "start": previous.start.isoformat(),
                "end": previous.end.isoformat(),
                "spent": str(previous.total) if previous.total is not None else None,
            }
        card = {
            "screen": "spending",
            "to": _link(
                "/spending",
                start=period.start.isoformat(),
                end=period.end.isoformat(),
                compare="1" if args.compare else None,
            ),
            "start": period.start.isoformat(),
            "end": period.end.isoformat(),
            "previous_start": previous.start.isoformat() if previous else None,
            "previous_end": previous.end.isoformat() if previous else None,
            "chart": stats.chart.model_dump(mode="json")
            if stats.chart and stats.chart.groups
            else None,
        }
        return Answer(json.dumps(figures), card)

    async def receipts(self, args: ReceiptArgs) -> Answer:
        """Receipts from a shop or holding an item over the period, and what they came to.

        For a shop, the receipts' spend; for an item, only what its lines cost — the rest
        of those receipts was not that item.
        """
        period = args.period(self.today)
        repository = ReceiptRepository(self.session)
        search = args.shop or args.item
        found, count = await repository.list_paginated(
            skip=0, limit=LISTED, period=period, search_query=search
        )
        figures: dict[str, Any] = {
            "start": period.start.isoformat(),
            "end": period.end.isoformat(),
            "currency": self.user.currency,
            "receipts": count,
            "latest": [
                {
                    "date": r.transaction_date.date().isoformat() if r.transaction_date else None,
                    "shop": r.merchant_name,
                    "total": str(r.total_amount) if r.total_amount is not None else None,
                }
                for r in found
            ],
        }
        if args.item:
            spend = await repository.item_spend(ItemView.ALL, search=args.item, period=period)
            figures["spent_on_item"] = str(spend.total)
        else:
            figures["spent"] = str(await repository.shop_spend(period, args.shop))
        card = {
            "screen": "receipts",
            "to": _link(
                "/receipts", start=period.start.isoformat(), end=period.end.isoformat(), q=search
            ),
        }
        return Answer(json.dumps(figures), card)

    async def product(self, args: ProductArgs) -> Answer:
        """A product's prices, shops and how its price moved (F16.2-3), all time by default."""
        products = ProductService(self.session)
        found = (await products.list_products(self.user.id, args.name))[:3]
        if not found:
            return Answer(json.dumps({"products": [], "note": "nothing bought by that name"}))
        period = DateRange(args.start, args.end or self.today) if args.start else None
        explored = await products.explore(self.user.id, [p.id for p in found], period)
        figures = {
            "currency": self.user.currency,
            "products": [
                {
                    "name": p.product.name,
                    "times_bought": p.amounts.times,
                    "spent": str(p.amounts.spent),
                    "price_change": {"first": str(p.change.first), "last": str(p.change.last)}
                    if p.change
                    else None,
                    "shops": [
                        {"shop": s.shop, "average": str(s.average), "latest": str(s.latest)}
                        for s in p.shops[:LISTED]
                    ],
                }
                for p in explored.products
            ],
        }
        card = {
            "screen": "products",
            "to": _link(
                "/products/explore",
                products=",".join(str(p.id) for p in found),
                start=period.start.isoformat() if period else None,
                end=period.end.isoformat() if period else None,
            ),
        }
        return Answer(json.dumps(figures), card)
