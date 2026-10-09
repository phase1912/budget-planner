"""A receipt with no readable date takes the day it was uploaded (BRD A11, D3).

Holding such a receipt until someone types a date stopped the upload dead — the wizard
has nowhere to type one — and kept real spending out of the month. The upload day is
almost always right, or close: people photograph receipts the day they shop. The
reading says the date was assumed, so the screen can say so and offer to change it.
"""

from datetime import date
from typing import Any


def with_upload_date(extraction: dict[str, Any], uploaded_on: date) -> dict[str, Any]:
    """The reading with `uploaded_on` as its date if it has none; otherwise unchanged.

    Marks an assumed date with `transaction_date_assumed` and a confidence of zero, so
    nothing downstream mistakes it for one read off the receipt. Leaves a failed
    reading alone: there is no receipt to date.
    """
    if "error" in extraction or extraction.get("transaction_date"):
        return extraction
    return {
        **extraction,
        "transaction_date": uploaded_on.isoformat(),
        "transaction_date_confidence": 0,
        "transaction_date_assumed": True,
    }
