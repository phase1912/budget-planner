"""Line names the user corrected, applied to the same shop's later receipts (F15.3)."""

from collections.abc import Iterable
from typing import Any, Protocol

from app.domain.categories import normalise_name


class RememberedCorrection(Protocol):
    """What applying a correction needs; `NameCorrection` satisfies it."""

    merchant_name: str
    read_name: str
    corrected_name: str


def apply_corrections(
    extraction: dict[str, Any], corrections: Iterable[RememberedCorrection]
) -> int:
    """Rename the lines this shop's remembered corrections cover, in place; returns how many.

    Only the receipt's own merchant counts, and only a printed name the user corrected
    before — exact once case and spacing are ignored, since a near match could rename a
    different product. What was printed is kept as `read_name` beside the new name, so the
    line can say it was corrected and be undone. A receipt with no merchant gets nothing.
    """
    merchant = normalise_name(extraction.get("merchant_name"))
    if not merchant:
        return 0
    known = {c.read_name: c.corrected_name for c in corrections if c.merchant_name == merchant}
    renamed = 0
    for line in extraction.get("line_items") or []:
        if not isinstance(line, dict):
            continue
        printed = str(line.get("name") or "")
        corrected = known.get(normalise_name(printed))
        if corrected and corrected != printed:
            line["read_name"] = printed
            line["name"] = corrected
            renamed += 1
    return renamed


def printed_name(line: dict[str, Any] | None, current: str) -> str:
    """What the receipt printed for a line: its `read_name` if it was corrected, else its name."""
    read = (line or {}).get("read_name")
    return read if isinstance(read, str) and read else current
