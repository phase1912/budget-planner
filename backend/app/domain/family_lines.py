"""What the family buys, line by line (F12.11): who buys what, what two of them bought
twice, and the swaps a family goal could be reached by.

Only shared receipts' lines come here (ADR-0017). Products are matched across members by
their key (`product_key`): each member's own product, printed differently by each shop, is
one name the family shares.
"""

import uuid
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.domain.products import product_key
from app.domain.purchases import PricePoint, cheaper_elsewhere

TWICE_WITHIN = timedelta(days=3)
"""Two members buying the same product this close together most likely bought it twice."""
TWICE_MAX = 5
PRODUCTS_MAX = 8
SWAPS_MAX = 5
WHOLE = Decimal("1")


@dataclass(frozen=True)
class FamilyLine:
    """One line of a shared receipt: who bought what, where, when and for how much."""

    member_id: uuid.UUID
    day: date
    name: str
    shop: str | None
    unit_price: Decimal
    quantity: Decimal
    paid: Decimal

    @property
    def key(self) -> str:
        return product_key(self.name).text or self.name.lower()


@dataclass(frozen=True)
class Twice:
    """A product two members bought within `TWICE_WITHIN`: the latest such pair."""

    name: str
    members: tuple[uuid.UUID, ...]
    days: tuple[date, ...]
    paid: Decimal


@dataclass(frozen=True)
class ProductByMember:
    """What the family paid for one product over the period, and by whom."""

    name: str
    total: Decimal
    members: dict[uuid.UUID, Decimal]


@dataclass(frozen=True)
class Swap:
    """Buying a product where the family has seen it cheaper, and what that saves a month."""

    name: str
    shop: str
    instead_of: str
    monthly_saving: Decimal


def _by_key(lines: Iterable[FamilyLine]) -> dict[str, list[FamilyLine]]:
    grouped: dict[str, list[FamilyLine]] = defaultdict(list)
    for line in sorted(lines, key=lambda line: line.day):
        grouped[line.key].append(line)
    return grouped


def bought_twice(lines: Iterable[FamilyLine]) -> list[Twice]:
    """Products two different members bought within three days of each other, latest first.

    One person buying bread every other day is a habit, not a double purchase, so only
    pairs of different members count. Each product appears once, by its latest pair.
    """
    found: list[Twice] = []
    for group in _by_key(lines).values():
        latest: tuple[FamilyLine, FamilyLine] | None = None
        for i, later in enumerate(group):
            for earlier in group[:i]:
                if earlier.member_id != later.member_id and later.day - earlier.day <= TWICE_WITHIN:
                    latest = (earlier, later)
        if latest is None:
            continue
        first, second = latest
        found.append(
            Twice(
                name=second.name,
                members=(first.member_id, second.member_id),
                days=(first.day, second.day),
                paid=first.paid + second.paid,
            )
        )
    found.sort(key=lambda t: (t.days[1], t.paid), reverse=True)
    return found[:TWICE_MAX]


def who_buys(lines: Iterable[FamilyLine]) -> list[ProductByMember]:
    """The products the family spends most on, each split by the member who bought it."""
    products: list[ProductByMember] = []
    for group in _by_key(lines).values():
        members: dict[uuid.UUID, Decimal] = defaultdict(Decimal)
        for line in group:
            members[line.member_id] += line.paid
        total = sum(members.values(), Decimal(0))
        products.append(ProductByMember(group[-1].name, total, dict(members)))
    products.sort(key=lambda p: (-p.total, p.name))
    return products[:PRODUCTS_MAX]


def swaps(
    lines: Sequence[FamilyLine], months: Decimal, today: date, freshness: timedelta
) -> list[Swap]:
    """Products the family last bought where they cost more than in a shop it also uses.

    Prices are the family's own, from any member's receipts: no outside price is assumed.
    The saving is the difference per item times how many the family buys a month; the
    biggest come first.
    """
    if months <= 0:
        return []
    found: list[Swap] = []
    for group in _by_key(lines).values():
        points = [PricePoint(line.day, line.shop, line.unit_price, None) for line in group]
        cheaper = cheaper_elsewhere(points, today, freshness)
        if cheaper is None:
            continue
        items = sum((line.quantity for line in group), Decimal(0)) / months
        saving = (cheaper.difference * items).quantize(WHOLE, ROUND_HALF_UP)
        if saving > 0:
            found.append(Swap(group[-1].name, cheaper.shop, cheaper.instead_of, saving))
    found.sort(key=lambda s: (-s.monthly_saving, s.name))
    return found[:SWAPS_MAX]
