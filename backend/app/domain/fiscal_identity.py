"""The numbers that make a fiscal receipt unique (F11.3, ADR-0015).

Every fiscal receipt prints the cash register's unique number and its own number on that
register — in Poland the register's ECA/EAO… number and the printout number (`nr:85503`),
in Ukraine the register's fiscal number (ФН) and the receipt's. Together they identify one
receipt for good, however it reached the user, which is what lets a second copy of it be
recognised exactly rather than guessed at by merchant, date and total (A14, F11.5).
"""

import re
from typing import Any

_NOISE = re.compile(r"^(nr|no|n°|№|фн|чек|id)[\s.:#]*", re.IGNORECASE)
_KEEP = re.compile("[^0-9A-Z\u0400-\u04ff]")  # digits, Latin and Cyrillic capitals

MIN_REGISTER_LENGTH = 6
"""Shorter than any real register number: a misread fragment, not an identity."""


def normalise(value: Any) -> str | None:
    """A printed fiscal number reduced to its letters and digits, upper-cased.

    `ECA 2201079960` → `ECA2201079960`, `nr:85503` → `85503`, `ФН 3000898168` →
    `3000898168`. None for anything empty or with no digit in it.
    """
    if value is None:
        return None
    text = _KEEP.sub("", _NOISE.sub("", str(value).strip()).upper())
    return text if any(c.isdigit() for c in text) else None


def fiscal_identity(extraction: dict[str, Any]) -> tuple[str, str] | None:
    """The receipt's (register, receipt number), or None unless both were read.

    Half an identity identifies nothing: a register prints thousands of receipts, and
    receipt numbers repeat across registers.
    """
    register = normalise(extraction.get("fiscal_register_id"))
    number = normalise(extraction.get("fiscal_receipt_number"))
    if not register or not number or len(register) < MIN_REGISTER_LENGTH:
        return None
    return register, number


def is_left_out(extraction: dict[str, Any]) -> bool:
    """Whether the wizard must not store this extraction, whatever the user selected.

    A receipt the user already has (same fiscal identity, F11.5) and one the user chose
    to skip as a duplicate (BRD A14) are never stored, and are not checked for the
    problems that would otherwise block storing the rest.
    """
    return bool(
        extraction.get("already_stored")
        or extraction.get("is_skipped")
        or extraction.get("duplicate_resolved") in ("skip", "skipped")
    )
