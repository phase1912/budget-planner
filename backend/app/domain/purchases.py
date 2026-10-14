"""Exploring what a user buys: how much, what it cost, and where it cost less (F16.2).

Quantities are kept apart by kind and never added across: pieces of a product with no
printed size, grams of one sold by weight or with a size in grams, millilitres likewise.
A price per kilogram or litre exists only where the product's size is known.
"""

import uuid
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.domain.categories import normalise_name

CENT = Decimal("0.01")
PIECE = "pc"


@dataclass(frozen=True)
class ProductFacts:
    """What the explorer needs of a product: its name and package size, if printed."""

    id: uuid.UUID
    name: str
    size_amount: Decimal | None
    size_unit: str | None


@dataclass(frozen=True)
class Purchase:
    """One line of a counted receipt that bought a selected product."""

    product_id: uuid.UUID
    day: date
    shop: str | None
    quantity: Decimal
    unit_price: Decimal
    total: Decimal


@dataclass
class Amounts:
    """How much was bought, by kind: pieces, grams and millilitres, never summed together."""

    times: int = 0
    spent: Decimal = Decimal(0)
    quantities: dict[str, Decimal] = field(default_factory=dict)

    def add(self, purchase: Purchase, product: ProductFacts) -> None:
        self.times += 1
        self.spent += purchase.total
        unit, amount = quantity_of(product, purchase.quantity)
        total = self.quantities.get(unit, Decimal(0)) + amount
        self.quantities[unit] = total.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class PricePoint:
    """What one purchase cost a unit, and per kilogram or litre where the size is known."""

    day: date
    shop: str | None
    unit_price: Decimal
    base_price: Decimal | None


@dataclass(frozen=True)
class PriceChange:
    """How the price moved from the first purchase in the period to the last."""

    first: Decimal
    last: Decimal
    difference: Decimal
    percent: Decimal | None


@dataclass(frozen=True)
class ShopPrice:
    """A product's price in one shop over the period, and how much above the cheapest it is."""

    shop: str
    purchases: int
    average: Decimal
    latest: Decimal
    latest_day: date
    above_cheapest: Decimal
    above_percent: Decimal | None


@dataclass
class ProductPurchases:
    """One selected product over the period."""

    product: ProductFacts
    amounts: Amounts
    prices: list[PricePoint]
    change: PriceChange | None
    shops: list[ShopPrice]


@dataclass
class MonthPurchases:
    """The selection's purchases in one calendar month."""

    month: date
    amounts: Amounts


@dataclass
class Exploration:
    """The whole answer for a selection and a period (F16.2)."""

    totals: Amounts
    months: list[MonthPurchases]
    products: list[ProductPurchases]


def quantity_of(product: ProductFacts, quantity: Decimal) -> tuple[str, Decimal]:
    """How much `quantity` of a product is: grams or millilitres when its size is printed,
    else pieces."""
    if product.size_amount is not None and product.size_unit in ("g", "ml"):
        return product.size_unit, quantity * product.size_amount
    return PIECE, quantity


def base_price(product: ProductFacts, unit_price: Decimal) -> Decimal | None:
    """The price per kilogram or litre of a product with a printed size; else None."""
    if not product.size_amount or product.size_unit not in ("g", "ml"):
        return None
    return (unit_price * 1000 / product.size_amount).quantize(CENT, rounding=ROUND_HALF_UP)


def _percent(part: Decimal, whole: Decimal) -> Decimal | None:
    if not whole:
        return None
    return (part * 100 / whole).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def price_change(points: Sequence[PricePoint]) -> PriceChange | None:
    """The move from the first purchase's price to the last; None for fewer than two.

    Compared per kilogram or litre where known, so a change of pack is not a change of price.
    """
    if len(points) < 2:
        return None
    first, last = points[0], points[-1]
    a = first.base_price if first.base_price is not None else first.unit_price
    b = last.base_price if last.base_price is not None else last.unit_price
    return PriceChange(a, b, b - a, _percent(b - a, a))


def shop_prices(points: Sequence[PricePoint]) -> list[ShopPrice]:
    """Each shop's average and latest price, cheapest latest first; empty under two shops.

    Shops are grouped ignoring case and spacing and named as most often printed. How much
    more a shop charged is measured on the latest prices, which is what a shopper meets.
    """
    by_shop: dict[str, list[PricePoint]] = defaultdict(list)
    spellings: dict[str, Counter[str]] = defaultdict(Counter)
    for point in points:
        key = normalise_name(point.shop)
        if not key:
            continue
        by_shop[key].append(point)
        spellings[key][point.shop or ""] += 1
    if len(by_shop) < 2:
        return []

    def price(p: PricePoint) -> Decimal:
        return p.base_price if p.base_price is not None else p.unit_price

    rows = []
    for key, shop_points in by_shop.items():
        latest = max(shop_points, key=lambda p: p.day)
        average = sum((price(p) for p in shop_points), Decimal(0)) / len(shop_points)
        rows.append((spellings[key].most_common(1)[0][0], shop_points, average, latest))
    cheapest = min(price(r[3]) for r in rows)
    shops = [
        ShopPrice(
            shop=name,
            purchases=len(shop_points),
            average=average.quantize(CENT, rounding=ROUND_HALF_UP),
            latest=price(latest),
            latest_day=latest.day,
            above_cheapest=price(latest) - cheapest,
            above_percent=_percent(price(latest) - cheapest, cheapest),
        )
        for name, shop_points, average, latest in rows
    ]
    return sorted(shops, key=lambda s: (s.latest, s.shop.lower()))


def months_between(first: date, last: date) -> list[date]:
    """The first days of every calendar month from `first`'s to `last`'s, oldest first."""
    months, current = [], first.replace(day=1)
    while current <= last:
        months.append(current)
        current = current.replace(
            year=current.year + current.month // 12, month=current.month % 12 + 1
        )
    return months


def explore(
    products: Iterable[ProductFacts],
    purchases: Iterable[Purchase],
    span: tuple[date, date] | None,
) -> Exploration:
    """Count a selection's purchases over a period (F16.2).

    `span` is the period's first and last day; None means all time, from the first purchase
    to the last. Every month in it appears, an empty one with zeroes.
    """
    facts = {p.id: p for p in products}
    bought = sorted((p for p in purchases if p.product_id in facts), key=lambda p: p.day)
    first, last = (
        span
        if span
        else ((bought[0].day, bought[-1].day) if bought else (date.today(), date.today()))
    )
    months = {m: MonthPurchases(m, Amounts()) for m in months_between(first, last)}
    totals = Amounts()
    per_product: dict[uuid.UUID, tuple[Amounts, list[PricePoint]]] = {
        pid: (Amounts(), []) for pid in facts
    }
    for purchase in bought:
        product = facts[purchase.product_id]
        totals.add(purchase, product)
        month = months.get(purchase.day.replace(day=1))
        if month is not None:
            month.amounts.add(purchase, product)
        amounts, points = per_product[product.id]
        amounts.add(purchase, product)
        points.append(
            PricePoint(
                purchase.day,
                purchase.shop,
                purchase.unit_price,
                base_price(product, purchase.unit_price),
            )
        )
    return Exploration(
        totals=totals,
        months=list(months.values()),
        products=[
            ProductPurchases(facts[pid], amounts, points, price_change(points), shop_prices(points))
            for pid, (amounts, points) in per_product.items()
        ],
    )
