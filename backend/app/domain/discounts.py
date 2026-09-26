"""Discount lines, as Polish receipts print them: a negative line under the item it reduces.

Biedronka, Stokrotka and others print "OPUST -10,04" as a line of its own
directly beneath the discounted product. Read literally, it is a purchase with a
negative price that the categoriser files under Other, which makes the product
look dearer than it was and drives Other below zero. Folded into the line above,
the product carries what was actually paid for it, and the receipt still adds up
to its printed total.
"""

from decimal import Decimal, InvalidOperation
from typing import Any


def _amount(value: Any) -> Decimal | None:
    """A printed amount as a number, or None if it is not one ("7,49", "-4.99")."""
    try:
        amount = Decimal(str(value).strip().replace(" ", "").replace(",", "."))
    except InvalidOperation:
        return None
    return amount if amount.is_finite() else None


def _can_take_discount(line: Any, discount: dict[str, Any]) -> bool:
    """A product line printed on the same photo as the discount, so it can be the one reduced."""
    return (
        isinstance(line, dict)
        and (_amount(line.get("total_price")) or Decimal(0)) > 0
        and line.get("file_id") == discount.get("file_id")
    )


def fold_discounts(
    items: list[Any], matches: list[Any] | None = None
) -> tuple[list[Any], list[Any]]:
    """Merge each negative line into the nearest product line above it on the same photo.

    Works on the raw extraction dicts the upload job stores and returns new ones,
    leaving those given untouched. The receiving line's `total_price` becomes the net
    amount paid and `discount` records what was taken off, for the wizard to show;
    its unit price and quantity stay as printed. A negative line with no product
    above it is kept: dropping it would change the receipt's total.

    `matches` are the cross-photo position matches, which point at lines by index
    (BRD B2-B4). They are returned renumbered for the shorter list, and a match on a
    folded discount line is dropped: each copy of a discount printed on two photos
    has already folded into its own photo's copy of the product.
    """
    folded: list[Any] = []
    new_index: dict[int, int] = {}
    for old_index, original in enumerate(items):
        item = dict(original) if isinstance(original, dict) else original
        total = _amount(item.get("total_price")) if isinstance(item, dict) else None
        target = (
            next((line for line in reversed(folded) if _can_take_discount(line, item)), None)
            if total is not None and total < 0
            else None
        )
        if target is None or total is None:
            new_index[old_index] = len(folded)
            folded.append(item)
            continue
        net = (_amount(target.get("total_price")) or Decimal(0)) + total
        discount = (_amount(target.get("discount")) or Decimal(0)) - total
        target["total_price"] = str(net.quantize(Decimal("0.01")))
        target["discount"] = str(discount.quantize(Decimal("0.01")))

    renumbered = []
    for match in matches or []:
        a, b = match.get("item_a_index"), match.get("item_b_index")
        if a in new_index and b in new_index:
            renumbered.append({**match, "item_a_index": new_index[a], "item_b_index": new_index[b]})
    return folded, renumbered
