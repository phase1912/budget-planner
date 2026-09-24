"""The spending taxonomy's own rules: canonical order and the review gate.

Both live here rather than in the repository or a schema because two layers
need them and neither owns them — the repository sorts by the order, and the
API decides from the gate whether an item goes to the review queue (BRD C1-C3).
"""

import difflib
import enum
import uuid
from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal
from typing import Protocol

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


def confident_category(
    category_id: uuid.UUID | None, confidence: int | None, threshold: float
) -> uuid.UUID | None:
    """The category the agent may file an item under unreviewed, or None (BRD C2, C3).

    None means the item belongs in Uncategorized: the categoriser declined it,
    or placed it below the threshold. Callers substitute the fallback
    themselves, since only they hold its id.
    """
    if category_id is None or is_low_confidence(confidence, threshold):
        return None
    return category_id


class ItemView(enum.StrEnum):
    """The three lists on the categorisation screen (docs/design/screens/categorisation.html).

    `needs_review` is the queue itself (C3); `corrected` is what the owner
    reassigned by hand (C4); `all` is every item they have.
    """

    NEEDS_REVIEW = "needs_review"
    CORRECTED = "corrected"
    ALL = "all"


RULE_NAME_SIMILARITY = 0.8
"""How alike two item names must be for a correction rule to cover both (BRD C5, ADR-0008).

`difflib.SequenceMatcher` ratio on normalised names. 0.8 absorbs OCR noise and
punctuation ("Protein Bar XL" / "Protein Bar XL.") without letting unrelated
products from the same shop collide.
"""


def normalise_name(value: str | None) -> str:
    """Case- and whitespace-insensitive form of a merchant or item name, for rule matching."""
    return " ".join((value or "").lower().split())


class CorrectionRule(Protocol):
    """What rule matching needs from a stored rule; `CategoryRule` satisfies it."""

    merchant_name: str
    item_name: str
    category_id: uuid.UUID
    created_at: datetime


def match_rule(
    item_name: str, merchant_name: str | None, rules: Iterable[CorrectionRule]
) -> uuid.UUID | None:
    """The category a correction rule files this item under, or None (BRD C5, ADR-0008).

    A rule covers only its own merchant. Among those, an exact name beats a
    similar one, a closer name beats a looser one, and on a tie the newest
    rule wins, because it is the user's latest word. Rules outrank the
    categoriser; manual choices on stored items outrank rules (invariant 13).
    """
    merchant = normalise_name(merchant_name)
    name = normalise_name(item_name)
    best: tuple[float, datetime, uuid.UUID] | None = None
    for rule in rules:
        if rule.merchant_name != merchant:
            continue
        similarity = difflib.SequenceMatcher(None, rule.item_name, name).ratio()
        if similarity < RULE_NAME_SIMILARITY:
            continue
        candidate = (similarity, rule.created_at, rule.category_id)
        if best is None or candidate[:2] > best[:2]:
            best = candidate
    return best[2] if best else None
