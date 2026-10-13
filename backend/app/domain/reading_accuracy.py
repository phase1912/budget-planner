"""How often reading a receipt needs the user's correction (F15.4).

A receipt counts as corrected when the user changed what was read — a line, the total,
the date — or added a line the reader missed. A name the user's remembered correction
fixed on its own (F15.3) is not: that is reading working, and is counted apart.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.domain.categories import normalise_name

TOP_SHOPS = 5
"""How many shops the report names: the ones behind most corrections."""


def mark_corrected(extraction: dict[str, Any], line_index: int | None = None) -> None:
    """Record on an extracted receipt that the user corrected it, and which line if one."""
    extraction["user_corrected"] = True
    if line_index is not None:
        indices = set(extraction.get("corrected_line_indices") or [])
        indices.add(line_index)
        extraction["corrected_line_indices"] = sorted(indices)


def corrected_lines(extraction: dict[str, Any]) -> set[int]:
    """The indices of the extracted lines the user corrected or added."""
    return {i for i in extraction.get("corrected_line_indices") or [] if isinstance(i, int)}


@dataclass(frozen=True)
class ReceiptReading:
    """One stored receipt as the report sees it."""

    merchant: str | None
    read_on: date
    corrected: bool
    lines: int
    corrected_lines: int
    remembered_lines: int


@dataclass
class ShopAccuracy:
    """One shop's receipts and how many of them needed correcting."""

    merchant: str
    receipts: int = 0
    corrected: int = 0


@dataclass
class MonthAccuracy:
    """One month's receipts, by the day they were read, and how many needed correcting."""

    month: date
    receipts: int = 0
    corrected: int = 0


@dataclass
class AccuracyReport:
    """The share of receipts and lines the user had to correct, by shop and by month."""

    receipts: int = 0
    corrected_receipts: int = 0
    lines: int = 0
    corrected_lines: int = 0
    remembered_lines: int = 0
    shops: list[ShopAccuracy] = field(default_factory=list)
    months: list[MonthAccuracy] = field(default_factory=list)


def accuracy_report(readings: Iterable[ReceiptReading], months: list[date]) -> AccuracyReport:
    """Count corrections over the receipts read in `months` (first days, oldest first).

    Every month asked for appears, an empty one with zeroes, so the trend has no gaps.
    Shops are grouped ignoring case and spacing, named as most often printed, and only
    those with a correction are listed, most corrected first (F15.4).
    """
    report = AccuracyReport(months=[MonthAccuracy(m) for m in months])
    by_month = {m.month: m for m in report.months}
    shops: dict[str, ShopAccuracy] = {}
    spellings: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for reading in readings:
        month = by_month.get(reading.read_on.replace(day=1))
        if month is None:
            continue
        report.receipts += 1
        report.lines += reading.lines
        report.corrected_lines += reading.corrected_lines
        report.remembered_lines += reading.remembered_lines
        month.receipts += 1
        if reading.corrected:
            report.corrected_receipts += 1
            month.corrected += 1
        key = normalise_name(reading.merchant)
        if not key:
            continue
        spellings[key][reading.merchant or ""] += 1
        shop = shops.setdefault(key, ShopAccuracy(key))
        shop.receipts += 1
        shop.corrected += 1 if reading.corrected else 0
    for key, shop in shops.items():
        shop.merchant = max(spellings[key].items(), key=lambda kv: kv[1])[0]
    report.shops = sorted(
        (s for s in shops.values() if s.corrected),
        key=lambda s: (-s.corrected, -s.receipts, s.merchant),
    )[:TOP_SHOPS]
    return report
