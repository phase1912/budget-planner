"""Guards for the architecture reference delivered by F0.8.1.

No business behaviour is asserted here — these two files are documentation, not
code. The guard is structural: the sections and cross-references the ticket
requires exist, so a future edit that quietly drops one fails the suite instead of
only being noticed in review.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = REPO_ROOT / "docs" / "architecture"


def test_overview_covers_required_sections() -> None:
    text = (DOCS_DIR / "overview.md").read_text()
    assert "## Layers inside the API" in text
    assert "Router" in text and "Service" in text and "Repository" in text and "Port" in text
    assert "## The ingestion pipeline" in text
    assert "Upload returns before parsing finishes" in text
    assert "manual_review" in text
    assert "Position matching runs only within one physical receipt" in text
    assert "## Security posture" in text
    assert "## Deliberate non-goals" in text
    assert "docs/design/" in text, "the visual design reference (ADR-0004) must be cross-linked"
    assert re.search(r"same\s+commit", text)


def test_domain_model_covers_required_sections() -> None:
    text = (DOCS_DIR / "domain-model.md").read_text()
    assert "## Entities" in text
    assert "## Receipt lifecycle" in text
    assert "## Invariants" in text
    assert "## Open decisions" in text
    assert re.search(r"same\s+commit", text)


def test_domain_model_invariants_are_numbered_and_traced_to_brd_ids() -> None:
    text = (DOCS_DIR / "domain-model.md").read_text()
    invariants_section = text.split("## Invariants", 1)[1].split("## Open decisions", 1)[0]

    # Each numbered item may wrap onto a continuation line before the next "N. " marker;
    # join those back into one item so a citation on the wrapped line still counts.
    items: list[str] = []
    for line in invariants_section.splitlines():
        stripped = line.strip()
        if stripped[:2].rstrip(".").isdigit():
            items.append(stripped)
        elif items and stripped and not stripped.startswith("**"):
            items[-1] += " " + stripped

    assert len(items) >= 15
    # Almost every invariant cites the BRD requirement ID(s) it enforces. The one
    # deliberate exception is the Decimal-not-float rule, which is a general money-
    # handling convention (see CLAUDE.md) rather than something a single EARS ID
    # demands — so this checks "all but a couple", not "every single one", which
    # would force a fake citation onto that exception.
    cited = [item for item in items if "(" in item and ")" in item]
    uncited = [item for item in items if item not in cited]
    assert len(uncited) <= 2, f"too many invariants without a requirement-ID citation: {uncited}"


def test_known_gap_between_brd_and_groomed_backlog_is_recorded() -> None:
    """BR-7 (G1-G12) exists in the BRD, but E1 as groomed only covers G1-G7 —
    this must stay documented until a grooming pass closes it, not silently drop
    out of the doc."""
    text = (DOCS_DIR / "domain-model.md").read_text()
    assert "G8" in text
    assert "G9" in text and "G12" in text
    assert "IdentityLink" in text
