from enum import StrEnum
from typing import Protocol


class MatchResult(StrEnum):
    SAME = "same"
    DIFFERENT = "different"


class ComparisonNotPossible(Exception):
    """Raised when one or both items cannot be compared due to a failed parse (BRD B6)."""

    pass


class Position(Protocol):
    name: str
    unit_price: str
    quantity: str
    total_price: str


def match_positions(a: Position, b: Position, *, same_receipt: bool) -> MatchResult:
    """Decide whether two extracted line items are the same physical purchase.

    Used when one long receipt is photographed in overlapping shots, so an item
    caught in both frames is counted once (BRD B2-B4). Requires an exact match on
    name, unit price, quantity and total.

    `same_receipt` must be True only for photos of one physical receipt: identical
    items on two separate transactions are two real purchases, never a duplicate
    (BRD B9).

    Raises ComparisonNotPossible if either item came from a failed parse (BRD B6).
    """
    if not same_receipt:
        return MatchResult.DIFFERENT

    if not all([a.name, a.unit_price, a.quantity, a.total_price]):
        raise ComparisonNotPossible("Item A has missing fields")

    if not all([b.name, b.unit_price, b.quantity, b.total_price]):
        raise ComparisonNotPossible("Item B has missing fields")

    if (
        a.name == b.name
        and a.unit_price == b.unit_price
        and a.quantity == b.quantity
        and a.total_price == b.total_price
    ):
        return MatchResult.SAME

    return MatchResult.DIFFERENT
