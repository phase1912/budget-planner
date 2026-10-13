"""How sure the reader was of each line it read off a receipt (BRD A10 — F15.2)."""

from typing import Any


def is_doubtful(confidence: int | None, threshold: float) -> bool:
    """Whether a line was read too uncertainly to be trusted without a look (BRD A10).

    `confidence` is the reader's 0-100 score for the line; `threshold` is the 0.0-1.0
    fraction from `Settings.ocr_confidence_threshold`, which ADR-0005 forbids restating
    anywhere else. `None` means no score was kept — a line typed by hand, stored before
    scores were kept, or corrected by the user — and is never doubtful.
    """
    return confidence is not None and confidence < threshold * 100


def read_confidence(item: dict[str, Any]) -> int | None:
    """The reader's score for one extracted line, or None when it gave no usable one."""
    value = item.get("confidence")
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return max(0, min(100, int(value)))
