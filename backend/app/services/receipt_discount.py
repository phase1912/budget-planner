"""Taking off a receipt what was not paid (F23.7)."""

import uuid
from collections.abc import Sequence
from decimal import Decimal

from app.api.errors import DomainError, ProblemCode
from app.domain.discount import DiscountTooLarge, spread_discount
from app.models.receipt import Receipt


def apply_discount(
    receipt: Receipt, amount: Decimal | None, line_ids: Sequence[uuid.UUID] | None = None
) -> None:
    """Set the receipt's unprinted discount and each line's share of it; None takes it off.

    Spread over every line, or only over `line_ids` when given; the month, categories and
    statistics then count what was paid, while each line's shelf price is untouched.
    Raises DomainError (discount_too_large) when the discount is more than those lines
    cost, or names no line of this receipt.
    """
    for line in receipt.line_items:
        line.discount_share = Decimal("0.00")
    receipt.paid_discount = None
    if amount is None:
        return
    chosen = (
        [line for line in receipt.line_items if line.id in set(line_ids)]
        if line_ids
        else list(receipt.line_items)
    )
    try:
        if not chosen:
            raise DiscountTooLarge("No lines to take it off.")
        shares = spread_discount([line.total_price for line in chosen], amount)
    except DiscountTooLarge as error:
        raise DomainError(
            "The discount is more than the chosen lines cost.",
            code=ProblemCode.DISCOUNT_TOO_LARGE,
        ) from error
    for line, share in zip(chosen, shares, strict=True):
        line.discount_share = share
    receipt.paid_discount = amount


def respread_discount(receipt: Receipt) -> None:
    """After the lines were corrected, spread the receipt's discount over them again —
    over all of them, or not at all once it is more than they now cost."""
    if receipt.paid_discount is None:
        return
    try:
        apply_discount(receipt, receipt.paid_discount)
    except DomainError:
        apply_discount(receipt, None)
