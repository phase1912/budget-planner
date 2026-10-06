"""When a receipt's lines agree with its printed total (BRD A9, A11)."""

from decimal import Decimal

TOTAL_TOLERANCE = Decimal("0.01")
"""The most the lines may differ from the printed total and still agree: one grosz.

Weighed goods and per-line rounding leave a cent of slop that is no reason to hold
a receipt out of the month; anything more is a misread line and is.
"""


def lines_match_total(lines_sum: Decimal, printed_total: Decimal) -> bool:
    """Whether the line totals add up to what the receipt says was paid, within a grosz."""
    return abs(lines_sum - printed_total) <= TOTAL_TOLERANCE
