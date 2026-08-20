"""Guards for the BRD traceability report generator (F0.6.4).

`docs/planning/brd-traceability.md` is generated output (like `backlog.md`,
F0.8's `backlog_sync.py render`) — these tests guard that regenerating it
produces exactly the committed file, so a `.feature` file edited without
re-running the script is caught here instead of only in review, and that every
BRD requirement ID is accounted for even when no scenario yet covers it.
"""

from pathlib import Path

from scripts.generate_brd_traceability import brd_requirement_ids, build_report

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def test_committed_report_matches_freshly_generated_output() -> None:
    committed = (REPO_ROOT / "docs/planning/brd-traceability.md").read_text()

    assert build_report() == committed


def test_every_brd_requirement_id_appears_exactly_once() -> None:
    requirement_ids = brd_requirement_ids()

    assert len(requirement_ids) == len(set(requirement_ids))
    assert "A1" in requirement_ids
    assert "N6" in requirement_ids


def test_a_requirement_with_no_matching_scenario_is_reported_as_untraced() -> None:
    """E6 is BR-5's optional chart-data feature — the BRD names it but gives it no scenario."""
    report = build_report()

    assert "| E6 | _Not yet traced by a scenario._ |" in report
