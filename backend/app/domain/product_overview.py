"""Everything bought, at a glance: whose price moved, and which shop is cheapest (F23.5)."""

import uuid
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from app.domain.purchases import (
    RISE_MIN_PERCENT,
    PriceChange,
    PricePoint,
    ProductFacts,
    Purchase,
    price_change,
    shop_prices,
)

MOVES_MAX = 10
HISTORY_MAX = 6


@dataclass(frozen=True)
class PriceMove:
    """A product whose price for one item moved by RISE_MIN_PERCENT or more, either way."""

    product: ProductFacts
    change: PriceChange
    last_shop: str | None
    history: list[Decimal]


@dataclass(frozen=True)
class ShopStanding:
    """A shop: for how many products it was the cheapest, and what was paid above the
    cheapest price when buying them there."""

    shop: str
    cheapest_for: int
    paid_above: Decimal


@dataclass(frozen=True)
class ProductsOverview:
    moves: list[PriceMove]
    shops: list[ShopStanding]
    paid_above: Decimal


def products_overview(
    products: Iterable[ProductFacts], purchases: Iterable[Purchase]
) -> ProductsOverview:
    """The period's biggest price moves and each shop's standing, from the user's receipts.

    Prices are per item, as advice cites them: one product is one size. A move under
    RISE_MIN_PERCENT is noise and left out; the biggest moves, up or down, come first.
    A shop's `paid_above` is each product's latest price there above the cheapest shop's,
    times how often it was bought there — what shopping elsewhere would have saved, about.
    """
    facts = {p.id: p for p in products}
    points: dict[uuid.UUID, list[PricePoint]] = defaultdict(list)
    for purchase in sorted(purchases, key=lambda p: p.day):
        if purchase.product_id in facts:
            points[purchase.product_id].append(
                PricePoint(purchase.day, purchase.shop, purchase.unit_price, None)
            )

    moves: list[PriceMove] = []
    cheapest: Counter[str] = Counter()
    above: dict[str, Decimal] = defaultdict(Decimal)
    for product_id, history in points.items():
        change = price_change(history)
        if change and change.percent is not None and abs(change.percent) >= RISE_MIN_PERCENT:
            moves.append(
                PriceMove(
                    product=facts[product_id],
                    change=change,
                    last_shop=history[-1].shop,
                    history=[p.unit_price for p in history[-HISTORY_MAX:]],
                )
            )
        shops = shop_prices(history)
        if shops:
            cheapest[shops[0].shop] += 1
            for row in shops:
                above[row.shop] += row.above_cheapest * row.purchases
                cheapest.setdefault(row.shop, 0)

    moves.sort(key=lambda m: -abs(m.change.percent or Decimal(0)))
    standings = sorted(
        (ShopStanding(shop, count, above[shop]) for shop, count in cheapest.items()),
        key=lambda s: (-s.cheapest_for, s.paid_above, s.shop.lower()),
    )
    return ProductsOverview(
        moves=moves[:MOVES_MAX],
        shops=standings,
        paid_above=sum((s.paid_above for s in standings), Decimal(0)),
    )
