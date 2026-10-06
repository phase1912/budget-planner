"""Discount lines, as Polish receipts print them: a negative line under the item it reduces.

Biedronka, Stokrotka and others print "Rabat -10,04" or "OPUST -10,04" as a line of
its own directly beneath the discounted product. It stays a line of its own, so the
receipt reads as printed and its lines add up to what was paid. It takes the
category of the product it reduces: filed under Other it would make that product's
category look dearer than it was and drive Other below zero.
"""

from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
from typing import Any


def printed_amount(value: Any) -> Decimal | None:
    """A printed amount as a number, or None if it is not one ("7,49", "-4.99")."""
    try:
        amount = Decimal(str(value).strip().replace(" ", "").replace(",", "."))
    except InvalidOperation:
        return None
    return amount if amount.is_finite() else None


def _is_discount(line: Any) -> bool:
    return isinstance(line, dict) and (printed_amount(line.get("total_price")) or Decimal(0)) < 0


def _is_product(line: Any) -> bool:
    return isinstance(line, dict) and (printed_amount(line.get("total_price")) or Decimal(0)) > 0


def discounted_products(items: list[Any]) -> dict[int, int]:
    """For each discount line, the index of the product it reduces.

    That is the nearest product line above it printed on the same photo; a discount
    with none above it reduces nothing in particular and is left out.
    """
    targets: dict[int, int] = {}
    for index, line in enumerate(items):
        if not _is_discount(line):
            continue
        for above in range(index - 1, -1, -1):
            candidate = items[above]
            if _is_product(candidate) and candidate.get("file_id") == line.get("file_id"):
                targets[index] = above
                break
    return targets


def file_discounts_with_products(items: list[Any]) -> list[Any]:
    """The lines with each discount given its product's category, in new dicts.

    Lines stay as and where they were, so the receipt still adds up to its printed
    total and cross-photo matches still point at the right lines (BRD B2-B4).
    """
    filed = [dict(line) if isinstance(line, dict) else line for line in items]
    for discount, product in discounted_products(items).items():
        filed[discount]["category_id"] = filed[product].get("category_id")
        filed[discount]["category_confidence"] = filed[product].get("category_confidence")
    return filed


WHOLE_RECEIPT_DISCOUNT = "Rabat"
"""The name given to a discount the user adds because the reader missed it."""


def dominant_category[C](lines: Iterable[tuple[C | None, Decimal]]) -> C | None:
    """The category the most was spent on, for a discount on the receipt as a whole.

    A discount the reader missed cannot be traced to one product, so it is filed
    where most of the money went rather than left for the user to categorise.
    `lines` are (category, total) pairs; uncategorised and negative lines don't count.
    """
    spent: dict[C, Decimal] = {}
    for category, total in lines:
        if category is not None and total > 0:
            spent[category] = spent.get(category, Decimal(0)) + total
    return max(spent, key=lambda c: spent[c]) if spent else None
