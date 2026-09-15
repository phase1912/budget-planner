from enum import StrEnum
from typing import Any, Protocol


def are_photos_from_same_receipt(header_a: dict[str, Any], header_b: dict[str, Any]) -> bool:
    """Determine if two parsed photos belong to the same physical receipt.

    Enforces BRD B5 and B9 by checking that the transaction dates and merchant names
    do not conflict. If they definitively differ, the photos represent distinct receipts
    and their items must never be matched. Missing fields (None) are treated as non-conflicting.
    """
    date_a = header_a.get("transaction_date")
    date_b = header_b.get("transaction_date")
    if date_a and date_b and date_a != date_b:
        return False

    merchant_a = header_a.get("merchant_name")
    merchant_b = header_b.get("merchant_name")
    return not (merchant_a and merchant_b and merchant_a != merchant_b)


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
