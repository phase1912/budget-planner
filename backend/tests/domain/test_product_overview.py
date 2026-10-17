"""Everything bought at a glance (F23.5)."""

import uuid
from datetime import date
from decimal import Decimal

from app.domain.product_overview import products_overview
from app.domain.purchases import ProductFacts, Purchase

MILK = ProductFacts(uuid.uuid4(), "Milk", Decimal(1000), "ml")
BREAD = ProductFacts(uuid.uuid4(), "Bread", None, None)


def _buy(product: ProductFacts, day: int, shop: str, price: str) -> Purchase:
    p = Decimal(price)
    return Purchase(product.id, date(2026, 10, day), shop, Decimal(1), p, p)


def test_names_the_noticeable_price_moves_biggest_first_and_ignores_noise() -> None:
    result = products_overview(
        [MILK, BREAD],
        [
            _buy(MILK, 1, "Biedronka", "3.49"),
            _buy(MILK, 9, "Biedronka", "3.99"),
            _buy(BREAD, 2, "Lidl", "6.49"),
            _buy(BREAD, 8, "Lidl", "6.59"),  # +1.5%: noise
        ],
    )
    assert [m.product.name for m in result.moves] == ["Milk"]
    assert result.moves[0].change.percent == Decimal("14.3")
    assert result.moves[0].history == [Decimal("3.49"), Decimal("3.99")]


def test_ranks_shops_by_how_often_they_were_cheapest_and_what_was_paid_above_it() -> None:
    result = products_overview(
        [MILK, BREAD],
        [
            _buy(MILK, 1, "Lidl", "3.79"),
            _buy(MILK, 2, "Żabka", "4.69"),
            _buy(MILK, 3, "Żabka", "4.69"),
            _buy(BREAD, 2, "Lidl", "6.49"),
            _buy(BREAD, 4, "Żabka", "6.99"),
        ],
    )
    assert [(s.shop, s.cheapest_for) for s in result.shops] == [("Lidl", 2), ("Żabka", 0)]
    # Milk: 0.90 above Lidl, bought twice at Żabka; bread: 0.50 above, once.
    assert result.shops[1].paid_above == Decimal("2.30")
    assert result.paid_above == Decimal("2.30")
