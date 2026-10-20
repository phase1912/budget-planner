#!/usr/bin/env python
"""Score receipt reading against receipts with known answers (F15.5.4).

Each case is a folder holding the receipt's photos and an `expected.json`:

    {"receipt_total": "952.00",
     "line_items": [{"name": "Чорний дракон", "total_price": "235.00"},
                    {"name": "Знижка", "total_price": "-11.75"}]}

Every case is read with the configured model (LLM_MODEL), the reconciliation rules applied
as an upload applies them, and its lines matched to the expected ones by amount and a
similar name. Reported per case and overall: expected lines found, lines read that were
not there, whether the total and the lines agree, and the time it took.

The cases are people's receipts and stay out of git (evaluation/receipts/ is ignored);
only receipts their owners agreed to share go in.

Usage (in the backend container, or with the same environment):
    python scripts/evaluate_reading.py evaluation/receipts
"""

import asyncio
import json
import sys
import time
from dataclasses import dataclass
from decimal import Decimal
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PHOTO_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".pdf": "application/pdf",
}
SIMILAR_NAME = 0.6
"""How alike a read name must be to the expected one, once amounts agree."""


@dataclass(frozen=True)
class Score:
    """One case's result."""

    case: str
    expected: int
    found: int
    extra: int
    total_right: bool
    adds_up: bool
    seconds: float


def _amount(value: Any) -> Decimal | None:
    from app.domain.discounts import printed_amount

    return printed_amount(value)


def _similar(a: str, b: str) -> bool:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= SIMILAR_NAME


def score(case: str, expected: dict[str, Any], read: dict[str, Any], seconds: float) -> Score:
    """Match read lines to expected ones: same amount and a similar name, each used once."""
    from app.domain.receipt_reconciliation import lines_sum
    from app.domain.receipt_totals import lines_match_total

    left = list(read.get("line_items") or [])
    found = 0
    for want in expected["line_items"]:
        match = next(
            (
                got
                for got in left
                if _amount(got.get("total_price")) == _amount(want["total_price"])
                and _similar(str(got.get("name") or ""), want["name"])
            ),
            None,
        )
        if match is not None:
            found += 1
            left.remove(match)
    printed = _amount(read.get("receipt_total"))
    total = lines_sum(read)
    return Score(
        case=case,
        expected=len(expected["line_items"]),
        found=found,
        extra=len(left),
        total_right=printed == _amount(expected["receipt_total"]),
        adds_up=printed is not None and total is not None and lines_match_total(total, printed),
        seconds=seconds,
    )


async def read_case(folder: Path) -> dict[str, Any]:
    """Read one case's photos as an upload does: the model, then the reconciliation rules."""
    from app.adapters.vision_agent import VisionAgentAdapter
    from app.agent.factory import agent_from_settings
    from app.domain.receipt_reconciliation import reconcile_by_rules

    photos = sorted(p for p in folder.iterdir() if p.suffix.lower() in PHOTO_TYPES)
    reading = await VisionAgentAdapter(agent_from_settings()).parse(
        [p.read_bytes() for p in photos], mime_types=[PHOTO_TYPES[p.suffix.lower()] for p in photos]
    )
    extraction = reading.model_dump(mode="json")
    ruled = reconcile_by_rules(extraction)
    return ruled[1] if ruled else extraction


async def main(root: Path) -> None:
    scores = []
    for folder in sorted(p for p in root.iterdir() if (p / "expected.json").exists()):
        expected = json.loads((folder / "expected.json").read_text())
        started = time.monotonic()
        try:
            read = await read_case(folder)
        except Exception as exc:
            print(f"{folder.name}: failed — {exc}")
            continue
        scores.append(score(folder.name, expected, read, time.monotonic() - started))
    print(f"{'case':30} {'lines':>9} {'extra':>5} {'total':>5} {'adds':>5} {'sec':>5}")
    for s in scores:
        print(
            f"{s.case:30} {s.found:>4}/{s.expected:<4} {s.extra:>5} "
            f"{'yes' if s.total_right else 'no':>5} {'yes' if s.adds_up else 'no':>5} "
            f"{s.seconds:>5.0f}"
        )
    if scores:
        lines = sum(s.found for s in scores) / max(sum(s.expected for s in scores), 1)
        print(
            f"\nLines read right: {lines:.0%} · totals right: "
            f"{sum(s.total_right for s in scores)}/{len(scores)} · adding up: "
            f"{sum(s.adds_up for s in scores)}/{len(scores)}"
        )


if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1] if len(sys.argv) > 1 else "evaluation/receipts")))
