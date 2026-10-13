"""How often reading needs the user's correction (F15.4)."""

from datetime import date

from app.domain.reading_accuracy import (
    ReceiptReading,
    accuracy_report,
    corrected_lines,
    mark_corrected,
)
from app.services.reading_accuracy import last_months

MONTHS = [date(2026, 8, 1), date(2026, 9, 1), date(2026, 10, 1)]


def _read(
    merchant: str | None,
    day: date,
    *,
    corrected: bool = False,
    lines: int = 3,
    fixed: int = 0,
    remembered: int = 0,
) -> ReceiptReading:
    return ReceiptReading(merchant, day, corrected, lines, fixed, remembered)


def test_a_correction_marks_the_receipt_and_the_line() -> None:
    extraction: dict[str, object] = {}

    mark_corrected(extraction, 2)
    mark_corrected(extraction, 0)
    mark_corrected(extraction)

    assert extraction["user_corrected"] is True
    assert corrected_lines(extraction) == {0, 2}


def test_the_report_names_the_share_corrected_and_the_shops_behind_it() -> None:
    """The demo: 2 of 4 receipts needed a correction, both from one shop."""
    report = accuracy_report(
        [
            _read("Biedronka", date(2026, 10, 2), corrected=True, fixed=1),
            _read("BIEDRONKA", date(2026, 10, 5), corrected=True, fixed=2),
            _read("Lidl", date(2026, 10, 6)),
            _read("Biedronka", date(2026, 9, 9), remembered=1),
        ],
        MONTHS,
    )

    assert (report.receipts, report.corrected_receipts) == (4, 2)
    assert (report.lines, report.corrected_lines, report.remembered_lines) == (12, 3, 1)
    assert [(s.merchant, s.receipts, s.corrected) for s in report.shops] == [("Biedronka", 3, 2)]


def test_every_month_asked_for_appears_even_an_empty_one() -> None:
    report = accuracy_report([_read("Lidl", date(2026, 10, 1), corrected=True)], MONTHS)

    assert [(m.month, m.receipts, m.corrected) for m in report.months] == [
        (date(2026, 8, 1), 0, 0),
        (date(2026, 9, 1), 0, 0),
        (date(2026, 10, 1), 1, 1),
    ]


def test_a_receipt_read_before_the_period_is_not_counted() -> None:
    report = accuracy_report([_read("Lidl", date(2026, 7, 31), corrected=True)], MONTHS)

    assert (report.receipts, report.shops) == (0, [])


def test_the_last_months_cross_a_new_year() -> None:
    assert last_months(date(2026, 2, 14), 3) == [
        date(2025, 12, 1),
        date(2026, 1, 1),
        date(2026, 2, 1),
    ]
