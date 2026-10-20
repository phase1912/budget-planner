"""Making a receipt's lines agree with its total without asking the user (BRD A9, A11).

A reading whose lines miss the printed total used to stop the upload until the user
found the error by hand — work nobody does for a supermarket receipt. The causes seen
in practice are fixed by rule here, each only when it closes the gap exactly; what is
left goes back to the model (the service), and only a reading that still disagrees
reaches the user, told that the app already tried.
"""

import copy
import enum
import re
from collections.abc import Callable
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.domain.discounts import printed_amount
from app.domain.receipt_totals import lines_match_total


class Reconciliation(enum.StrEnum):
    """How a reading's lines came to agree with its total, or that they did not."""

    DEPOSIT = "deposit"
    """The total read was the goods subtotal; the bottle deposit paid on top was a line."""
    DISCOUNT_SIGN = "discount_sign"
    """A discount line was read without its minus sign."""
    DISCOUNT_TOTAL = "discount_total"
    """The footer's sum of the discounts was listed as a line, counting them twice."""
    REPEATED_LINE = "repeated_line"
    """A deposit or a subtotal was listed again as a line of its own."""
    LINE_ARITHMETIC = "line_arithmetic"
    """One line's total was misread; its quantity times unit price was right."""
    ROUNDING = "rounding"
    """The till's rounding of the amount to pay was not read as a line."""
    RECHECKED = "rechecked"
    """A second look at the photos corrected the lines."""
    UNRESOLVED = "unresolved"
    """Nothing worked: the user is asked, told that the app already tried."""


DEPOSIT_LINE = re.compile(r"kaucj|opakowa\w* zwrotn|\bdeposit\b|\bpfand\b|\bzastaw", re.IGNORECASE)
"""Returnable-packaging deposits: Poland's system kaucyjny since October 2025, and kin."""

DISCOUNT_LINE = re.compile(
    r"\b(opust|rabat|upust|zni[żz]k|promocj|discount|sleva|remise|sconto|descuento)"
    r"|(знижк|скидк|акці|акци)",
    re.IGNORECASE,
)
"""Names receipts give a line that takes money off, Polish, Ukrainian and others.

Cyrillic has no word boundary in Python's ASCII sense, hence its own alternative."""

SUMMARY_LINE = re.compile(
    r"\b(suma|razem|total|ptu|wydania|opakowania zwrotne)\b|(сума|разом|всього|до сплати)",
    re.IGNORECASE,
)
"""Footer lines that repeat amounts already counted: a section header or subtotal."""

ROUNDING_NAME = re.compile(r"zaokr|rounding|rundung|arrondi|округл", re.IGNORECASE)
"""A till's rounding of the amount to pay: a negative line, but not a discount."""

ROUNDING_LINE = "Rounding"
"""The name of a rounding line the reader missed; one it read keeps its printed name."""

MAX_ROUNDING = Decimal("0.50")
"""The most a till rounds the amount to pay (to the nearest whole unit at most). A gap
under it with nothing else to explain it is taken as that rounding: a product the
reader missed would cost more."""

CENT = Decimal("0.01")

Rule = Callable[[dict[str, Any], Decimal], dict[str, Any] | None]


def is_deposit(name: str) -> bool:
    """Whether a line is a returnable-packaging deposit, or one handed back."""
    return bool(DEPOSIT_LINE.search(name))


def _items(extraction: dict[str, Any]) -> list[dict[str, Any]]:
    items = extraction.get("line_items")
    return [i for i in items if isinstance(i, dict)] if isinstance(items, list) else []


def _counted(extraction: dict[str, Any]) -> list[int]:
    """Indices of the lines that count: a line caught in two overlapping shots counts once."""
    duplicates = {
        m.get("item_b_index")
        for m in extraction.get("position_matches") or []
        if isinstance(m, dict) and m.get("result") == "same"
    }
    return [i for i in range(len(_items(extraction))) if i not in duplicates]


def lines_sum(extraction: dict[str, Any]) -> Decimal | None:
    """What the counted lines add up to, or None if any of them has no readable amount."""
    items = _items(extraction)
    total = Decimal(0)
    for index in _counted(extraction):
        amount = printed_amount(items[index].get("total_price"))
        if amount is None:
            return None
        total += amount
    return total


def _agrees(extraction: dict[str, Any], printed: Decimal) -> bool:
    total = lines_sum(extraction)
    return total is not None and lines_match_total(total, printed)


def _with_deposit(extraction: dict[str, Any], printed: Decimal) -> dict[str, Any] | None:
    """Polish receipts print "SUMA PLN" for the goods and "DO ZAPŁATY" for what was paid,
    deposit included; a reader that took the first while listing the deposit is off by
    exactly the deposit, and the amount paid is the lines' sum."""
    items = _items(extraction)
    deposits = sum(
        (printed_amount(items[i].get("total_price")) or Decimal(0))
        for i in _counted(extraction)
        if is_deposit(str(items[i].get("name") or ""))
    )
    total = lines_sum(extraction)
    if not deposits or total is None or not lines_match_total(total - deposits, printed):
        return None
    fixed = copy.deepcopy(extraction)
    fixed["receipt_total"] = f"{total:.2f}"
    return fixed


def _discount_signs(extraction: dict[str, Any], printed: Decimal) -> dict[str, Any] | None:
    """A discount line read as a positive amount: flip the ones that need it."""
    items = _items(extraction)
    unsigned = [
        i
        for i in _counted(extraction)
        if DISCOUNT_LINE.search(str(items[i].get("name") or ""))
        and (printed_amount(items[i].get("total_price")) or Decimal(0)) > 0
    ]
    candidates = [[i] for i in unsigned] + ([unsigned] if len(unsigned) > 1 else [])
    for flip in candidates:
        fixed = copy.deepcopy(extraction)
        for i in flip:
            amount = printed_amount(fixed["line_items"][i]["total_price"]) or Decimal(0)
            fixed["line_items"][i]["total_price"] = f"{-amount:.2f}"
        if _agrees(fixed, printed):
            return fixed
    return None


def _discount_total(extraction: dict[str, Any], printed: Decimal) -> dict[str, Any] | None:
    """A footer "Знижка -48.90" that sums the discounts printed under each product, read
    as one more discount: the lines fall short by exactly it. Drop that line."""
    items = _items(extraction)
    amounts = {
        i: printed_amount(items[i].get("total_price")) or Decimal(0)
        for i in _counted(extraction)
        if not ROUNDING_NAME.search(str(items[i].get("name") or ""))
    }
    discounts = [i for i, amount in amounts.items() if amount < 0]
    for i in reversed(discounts):
        others = sum((amounts[j] for j in discounts if j != i), Decimal(0))
        if len(discounts) < 2 or not lines_match_total(amounts[i], others):
            continue
        fixed = copy.deepcopy(extraction)
        del fixed["line_items"][i]
        fixed["position_matches"] = []
        if _agrees(fixed, printed):
            return fixed
    return None


def _rounding(extraction: dict[str, Any], printed: Decimal) -> dict[str, Any] | None:
    """The till rounded the amount to pay ("Округлення -0.11") and the reader missed the
    line: a gap under MAX_ROUNDING becomes a rounding line, so the total stays as paid."""
    total = lines_sum(extraction)
    if total is None:
        return None
    gap = printed - total
    if not CENT < abs(gap) < MAX_ROUNDING:
        return None
    fixed = copy.deepcopy(extraction)
    last = _items(extraction)[-1] if _items(extraction) else {}
    fixed["line_items"].append(
        {
            "name": ROUNDING_LINE,
            "quantity": "1",
            "unit_price": f"{gap:.2f}",
            "total_price": f"{gap:.2f}",
            "file_id": last.get("file_id"),
        }
    )
    return fixed


def _is_summary(item: dict[str, Any]) -> bool:
    return bool(SUMMARY_LINE.search(str(item.get("name") or "")))


def _repeated_line(extraction: dict[str, Any], printed: Decimal) -> dict[str, Any] | None:
    """A deposit or subtotal read twice — "OPAKOWANIA ZWROTNE WYDANIA 3,00" above "But
    Plastik kaucja 3,00" — leaves the lines over by exactly that line: drop it. Only
    deposit and footer lines are candidates; two equal products are two purchases."""
    items = _items(extraction)
    total = lines_sum(extraction)
    if total is None or total <= printed:
        return None
    gap = total - printed
    candidates = [
        i
        for i in _counted(extraction)
        if printed_amount(items[i].get("total_price")) == gap
        and (is_deposit(str(items[i].get("name") or "")) or _is_summary(items[i]))
    ]
    # A heading or subtotal is the likelier repeat than the line that names the deposit.
    for i in sorted(candidates, key=lambda c: not _is_summary(items[c])):
        fixed = copy.deepcopy(extraction)
        del fixed["line_items"][i]
        fixed["position_matches"] = []
        if _agrees(fixed, printed):
            return fixed
    return None


def _line_arithmetic(extraction: dict[str, Any], printed: Decimal) -> dict[str, Any] | None:
    """One line whose total disagrees with its quantity times unit price, and the product
    is what makes the receipt add up: the total was misread, the other two were not."""
    items = _items(extraction)
    for i in _counted(extraction):
        quantity = printed_amount(items[i].get("quantity"))
        unit = printed_amount(items[i].get("unit_price"))
        total = printed_amount(items[i].get("total_price"))
        if quantity is None or unit is None or total is None or total <= 0:
            continue
        product = (quantity * unit).quantize(CENT, ROUND_HALF_UP)
        if abs(product - total) <= CENT:
            continue
        fixed = copy.deepcopy(extraction)
        fixed["line_items"][i]["total_price"] = f"{product:.2f}"
        if _agrees(fixed, printed):
            return fixed
    return None


RULES: tuple[tuple[Reconciliation, Rule], ...] = (
    (Reconciliation.DEPOSIT, _with_deposit),
    (Reconciliation.DISCOUNT_SIGN, _discount_signs),
    (Reconciliation.DISCOUNT_TOTAL, _discount_total),
    (Reconciliation.REPEATED_LINE, _repeated_line),
    (Reconciliation.LINE_ARITHMETIC, _line_arithmetic),
    (Reconciliation.ROUNDING, _rounding),
)


def reconcile_by_rules(extraction: dict[str, Any]) -> tuple[Reconciliation, dict[str, Any]] | None:
    """The first rule that makes the lines agree with the total, and the corrected reading.

    Leaves `extraction` untouched. None when the lines already agree, when either side
    is unreadable, or when no rule closes the gap exactly.
    """
    printed = printed_amount(extraction.get("receipt_total"))
    if printed is None or lines_sum(extraction) is None or _agrees(extraction, printed):
        return None
    for how, rule in RULES:
        fixed = rule(extraction, printed)
        if fixed is not None:
            return how, fixed
    return None


def accepts_recheck(before: dict[str, Any], after: dict[str, Any]) -> bool:
    """Whether a second reading may replace the first.

    Only when its lines now agree with the total, and with the same total: a model
    asked to make the numbers meet could otherwise just rewrite the total, which is
    the one figure the user can check against their bank.
    """
    printed = printed_amount(before.get("receipt_total"))
    if printed is None or printed_amount(after.get("receipt_total")) != printed:
        return False
    return _agrees(after, printed)
