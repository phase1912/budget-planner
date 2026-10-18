"""A discount the receipt does not print: a gift card, a voucher, a deal at the till (F23.7)."""

from collections.abc import Sequence
from decimal import ROUND_DOWN, Decimal

CENT = Decimal("0.01")


class DiscountTooLarge(ValueError):
    """The discount is more than the lines it is spread over cost."""


def spread_discount(totals: Sequence[Decimal], amount: Decimal) -> list[Decimal]:
    """Each line's share of `amount`, in proportion to what it cost, summing to it exactly.

    Shares are cut to the grosz and the pennies left over go to the dearest line, so the
    lines' categories count what was really paid and nothing is lost to rounding. A line
    that cost nothing, or a refund line, takes no share.

    Raises DiscountTooLarge when `amount` is more than the lines cost, ValueError when it
    is not above zero.
    """
    if amount <= 0:
        raise ValueError("A discount is more than zero.")
    weights = [max(total, Decimal(0)) for total in totals]
    whole = sum(weights, Decimal(0))
    if amount > whole:
        raise DiscountTooLarge(f"{amount} is more than the {whole} the lines cost.")
    shares = [(amount * w / whole).quantize(CENT, rounding=ROUND_DOWN) for w in weights]
    dearest = max(range(len(weights)), key=lambda i: weights[i])
    shares[dearest] += amount - sum(shares, Decimal(0))
    return shares
