"""The spending taxonomy's own rules: canonical order and the review gate.

Both live here rather than in the repository or a schema because two layers
need them and neither owns them — the repository sorts by the order, and the
API decides from the gate whether an item goes to the review queue (BRD C1-C3).
"""

from decimal import Decimal

UNCATEGORIZED = "Uncategorized"

DEFAULT_CATEGORY_ORDER: tuple[str, ...] = (
    "Groceries",
    "Dining",
    "Transport",
    "Utilities",
    "Health",
    "Entertainment",
    "Other",
    UNCATEGORIZED,
)
"""The built-in categories in the order the BRD lists them (C1).

Not alphabetical: the reference screen (`docs/design/screens/categories.html`)
reads as a spending narrative, and `Uncategorized` sits last because it is the
absence of a decision rather than one more kind of spending.
"""


def is_low_confidence(confidence: int | None, threshold: float) -> bool:
    """Decide whether a category assignment is too weak to stand unreviewed.

    `confidence` is the categoriser's 0-100 score; `threshold` is the 0.0-1.0
    fraction from `Settings.categorization_confidence_threshold`, which ADR-0005
    fixes at 0.70 and forbids restating as a literal anywhere else.

    A `None` confidence means nothing categorised the item — not that it was
    categorised badly — so it is not reported as a weak assignment. Treating the
    two alike would flood F5.3's queue with items the agent never saw (BRD C3).
    """
    if confidence is None:
        return False
    return Decimal(confidence) / Decimal(100) < Decimal(str(threshold))
