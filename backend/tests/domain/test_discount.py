"""A discount the receipt does not print (F23.7)."""

from decimal import Decimal

import pytest

from app.domain.discount import DiscountTooLarge, spread_discount


def test_a_discount_is_spread_in_proportion_and_adds_up_to_the_grosz() -> None:
    lines = [
        Decimal("59.99"),
        Decimal("49.99"),
        Decimal("24.99"),
        Decimal("21.04"),
        Decimal("12.99"),
    ]
    shares = spread_discount(lines, Decimal("100.00"))

    assert sum(shares) == Decimal("100.00")
    assert shares[0] == max(shares)
    # Coffee, a third of the receipt, takes about a third of the discount.
    assert Decimal("35") < shares[0] < Decimal("36")


def test_a_refund_line_takes_no_share() -> None:
    assert spread_discount([Decimal("10.00"), Decimal("-2.00")], Decimal("5.00")) == [
        Decimal("5.00"),
        Decimal("0.00"),
    ]


def test_a_discount_larger_than_the_lines_is_refused() -> None:
    with pytest.raises(DiscountTooLarge):
        spread_discount([Decimal("10.00")], Decimal("10.01"))
