"""Exploring what a user buys: how much, what it cost, and where it cost less (F16.2).

Quantities are kept apart by kind and never added across: pieces of a product with no
printed size, grams of one sold by weight or with a size in grams, millilitres likewise.
A price per kilogram or litre exists only where the product's size is known.
"""

import uuid
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
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
    """The selection's purchases in one calendar month; `by_product` is what each product
    cost in it, for a column stacked by product (explore.html)."""

    month: date
    amounts: Amounts
    by_product: dict[uuid.UUID, Decimal] = field(default_factory=dict)


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
            month.by_product[product.id] = (
                month.by_product.get(product.id, Decimal(0)) + purchase.total
            )
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


@dataclass(frozen=True)
class CheaperShop:
    """Where a product recently cost less than at the shop it was last bought in (F16.3)."""

    shop: str
    instead_of: str
    difference: Decimal
    percent: Decimal | None


def cheaper_elsewhere(
    points: Sequence[PricePoint], today: date, freshness: timedelta
) -> CheaperShop | None:
    """The cheaper shop for a product, if the user did not last buy it there (F16.3).

    Only prices within `freshness` of `today` count, so a price from long ago never makes
    a shop look cheaper. Measured on each shop's latest price for one item against the one
    where the last purchase was; None with fewer than two such shops, or
    when the last purchase already was the cheapest.
    """
    # Every purchase of one product is the same size, so the price of one is the plainest
    # measure: "1.00 less", not "50.00 less per kg" for a 20 g egg.
    fresh = [
        PricePoint(p.day, p.shop, p.unit_price, None) for p in points if p.day >= today - freshness
    ]
    shops = shop_prices(fresh)
    if len(shops) < 2:
        return None
    last = normalise_name(max(fresh, key=lambda p: p.day).shop)
    current = next((s for s in shops if normalise_name(s.shop) == last), None)
    cheapest = shops[0]
    if current is None or normalise_name(cheapest.shop) == last:
        return None
    difference = current.latest - cheapest.latest
    if difference <= 0:
        return None
    return CheaperShop(
        shop=cheapest.shop,
        instead_of=current.shop,
        difference=difference,
        percent=_percent(difference, current.latest),
    )


RISE_MIN_PERCENT = Decimal(5)
"""A price that moved less than this is noise, not a rise worth citing."""
SIGNALS_MAX = 10


@dataclass(frozen=True)
class PriceSignal:
    """What advice may cite about one product's price (F16.4).

    `cheaper` is where it recently cost less than where it was last bought; `rise` how its
    price for one item moved over the window, kept only from RISE_MIN_PERCENT up. `monthly_items` is
    how many were bought a month on average, `monthly_spend` what they cost a month.
    """

    product: str
    cheaper: CheaperShop | None
    rise: PriceChange | None
    monthly_items: Decimal
    monthly_spend: Decimal


def price_signals(
    products: Iterable[ProductFacts],
    purchases: Iterable[Purchase],
    months: Decimal,
    today: date,
    freshness: timedelta,
) -> list[PriceSignal]:
    """The products whose price is worth citing: a cheaper shop or a real rise (F16.4).

    `purchases` are the window's, `months` its length in months. Ordered by what a switch
    would save a month, then by the size of the rise; at most SIGNALS_MAX.
    """
    facts = {p.id: p for p in products}
    bought: dict[uuid.UUID, list[Purchase]] = defaultdict(list)
    for purchase in sorted(purchases, key=lambda p: p.day):
        if purchase.product_id in facts:
            bought[purchase.product_id].append(purchase)
    signals = []
    for product_id, lines in bought.items():
        product = facts[product_id]
        # Per item, like the cheaper shop: one product is one size, and "6.49 to 7.49 each"
        # reads plainer to the model and the user than the same move per kilogram.
        points = [PricePoint(p.day, p.shop, p.unit_price, None) for p in lines]
        change = price_change(points)
        rise = change if change and change.percent and change.percent >= RISE_MIN_PERCENT else None
        cheaper = cheaper_elsewhere(points, today, freshness)
        if cheaper is None and rise is None:
            continue
        items = sum((p.quantity for p in lines), Decimal(0))
        spend = sum((p.total for p in lines), Decimal(0))
        signals.append(
            PriceSignal(
                product=product.name,
                cheaper=cheaper,
                rise=rise,
                monthly_items=(items / months).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP),
                monthly_spend=(spend / months).quantize(CENT, rounding=ROUND_HALF_UP),
            )
        )

    def saving(s: PriceSignal) -> Decimal:
        return s.cheaper.difference * s.monthly_items if s.cheaper else Decimal(0)

    signals.sort(key=lambda s: (-saving(s), -(s.rise.percent or 0) if s.rise else 0, s.product))
    return signals[:SIGNALS_MAX]
