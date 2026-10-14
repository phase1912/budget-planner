"""Exploring a selection of products: amounts, prices and shops (F16.2)."""

import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.domain.purchases import (
    PricePoint,
    ProductFacts,
    Purchase,
    cheaper_elsewhere,
    explore,
    months_between,
    price_signals,
)

CHIPS = ProductFacts(uuid.uuid4(), "Chipsy Lay's 140g", Decimal(140), "g")
CROUTONS = ProductFacts(uuid.uuid4(), "Sucharki 150g", Decimal(150), "g")
BAG = ProductFacts(uuid.uuid4(), "Torba", None, None)


def _bought(product: ProductFacts, day: date, shop: str, price: str, qty: str = "1") -> Purchase:
    unit = Decimal(price)
    return Purchase(product.id, day, shop, Decimal(qty), unit, unit * Decimal(qty))


def test_the_selection_is_counted_in_weight_and_pieces_never_added_together() -> None:
    """The demo: chips and croutons this month, and a bag that has no weight."""
    result = explore(
        [CHIPS, CROUTONS, BAG],
        [
            _bought(CHIPS, date(2026, 10, 2), "Biedronka", "6.99", "2"),
            _bought(CROUTONS, date(2026, 10, 3), "Lidl", "3.49"),
            _bought(BAG, date(2026, 10, 3), "Lidl", "0.50", "3"),
        ],
        (date(2026, 10, 1), date(2026, 10, 31)),
    )

    assert result.totals.times == 3
    assert result.totals.spent == Decimal("18.97")
    assert result.totals.quantities == {"g": Decimal(430), "pc": Decimal(3)}


def test_every_month_of_the_period_appears_even_without_purchases() -> None:
    result = explore(
        [CHIPS],
        [_bought(CHIPS, date(2026, 10, 2), "Biedronka", "6.99")],
        (date(2026, 8, 15), date(2026, 10, 31)),
    )

    assert [(m.month, m.amounts.times) for m in result.months] == [
        (date(2026, 8, 1), 0),
        (date(2026, 9, 1), 0),
        (date(2026, 10, 1), 1),
    ]


def test_a_price_rise_is_measured_per_kilogram_from_first_purchase_to_last() -> None:
    result = explore(
        [CHIPS],
        [
            _bought(CHIPS, date(2026, 6, 1), "Biedronka", "6.30"),
            _bought(CHIPS, date(2026, 10, 1), "Biedronka", "6.93"),
        ],
        None,
    )

    chips = result.products[0]
    assert [p.base_price for p in chips.prices] == [Decimal("45.00"), Decimal("49.50")]
    assert chips.change is not None
    assert (chips.change.difference, chips.change.percent) == (Decimal("4.50"), Decimal("10.0"))


def test_each_shop_is_measured_against_the_cheapest_on_latest_prices() -> None:
    """The demo: Lay's at 6.99 in Biedronka and 8.49 in Żabka, 21% more."""
    result = explore(
        [CHIPS],
        [
            _bought(CHIPS, date(2026, 9, 1), "Żabka", "7.99"),
            _bought(CHIPS, date(2026, 10, 1), "ŻABKA", "8.49"),
            _bought(CHIPS, date(2026, 10, 2), "Biedronka", "6.99"),
        ],
        None,
    )

    shops = result.products[0].shops
    assert [(s.shop, s.purchases) for s in shops] == [("Biedronka", 1), ("Żabka", 2)]
    zabka = shops[1]
    # Per kilogram, as the product's size is printed: 60.64 against 49.93.
    assert (zabka.latest, zabka.above_cheapest, zabka.above_percent) == (
        Decimal("60.64"),
        Decimal("10.71"),
        Decimal("21.5"),
    )


def test_one_shop_is_nothing_to_compare() -> None:
    result = explore([CHIPS], [_bought(CHIPS, date(2026, 10, 1), "Lidl", "6.99")], None)

    assert result.products[0].shops == []
    assert result.products[0].change is None


def test_the_months_between_two_days_cross_a_new_year() -> None:
    assert months_between(date(2025, 12, 20), date(2026, 1, 5)) == [
        date(2025, 12, 1),
        date(2026, 1, 1),
    ]


def _point(day: date, shop: str, price: str) -> PricePoint:
    return PricePoint(day, shop, Decimal(price), None)


TODAY = date(2026, 10, 14)
FRESH = timedelta(days=90)


def test_a_cheaper_shop_is_named_against_where_it_was_last_bought() -> None:
    """F16.3: last bought at Biedronka for 4.99; Lidl had it for 4.49 last week."""
    found = cheaper_elsewhere(
        [
            _point(date(2026, 10, 7), "Lidl", "4.49"),
            _point(date(2026, 10, 12), "Biedronka", "4.99"),
        ],
        TODAY,
        FRESH,
    )

    assert found is not None
    assert (found.shop, found.instead_of, found.difference, found.percent) == (
        "Lidl",
        "Biedronka",
        Decimal("0.50"),
        Decimal("10.0"),
    )


def test_a_price_from_long_ago_never_makes_a_shop_cheaper() -> None:
    found = cheaper_elsewhere(
        [_point(date(2025, 9, 1), "Lidl", "3.99"), _point(date(2026, 10, 12), "Biedronka", "4.99")],
        TODAY,
        FRESH,
    )

    assert found is None


def test_nothing_is_said_when_the_last_purchase_was_already_the_cheapest() -> None:
    found = cheaper_elsewhere(
        [
            _point(date(2026, 10, 7), "Biedronka", "4.99"),
            _point(date(2026, 10, 12), "Lidl", "4.49"),
        ],
        TODAY,
        FRESH,
    )

    assert found is None


def test_price_signals_name_cheaper_shops_and_real_rises_most_saving_first() -> None:
    """F16.4: chips bought cheaper elsewhere, croutons up 20%, a bag steady."""
    purchases = [
        _bought(CHIPS, date(2026, 10, 1), "Biedronka", "6.99"),
        _bought(CHIPS, date(2026, 10, 10), "Zabka", "8.49", "2"),
        _bought(CROUTONS, date(2026, 8, 1), "Lidl", "3.00"),
        _bought(CROUTONS, date(2026, 10, 1), "Lidl", "3.60"),
        _bought(BAG, date(2026, 8, 1), "Lidl", "0.50"),
        _bought(BAG, date(2026, 10, 1), "Lidl", "0.51"),
    ]

    signals = price_signals([CHIPS, CROUTONS, BAG], purchases, Decimal(3), TODAY, FRESH)

    assert [s.product for s in signals] == ["Chipsy Lay's 140g", "Sucharki 150g"]
    chips, croutons = signals
    assert chips.cheaper is not None and chips.cheaper.difference == Decimal("1.50")
    assert chips.monthly_items == Decimal("1.0")
    assert croutons.cheaper is None
    assert croutons.rise is not None and croutons.rise.percent == Decimal("20.0")
