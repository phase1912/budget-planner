"""A receipt with no readable date takes the day it was uploaded (BRD A11, D3)."""

from datetime import date

from app.domain.receipt_dates import with_upload_date


def test_an_undated_receipt_takes_its_upload_day_and_says_so() -> None:
    dated = with_upload_date(
        {"transaction_date": None, "receipt_total": "1197.00"}, date(2026, 10, 9)
    )

    assert dated["transaction_date"] == "2026-10-09"
    assert (dated["transaction_date_assumed"], dated["transaction_date_confidence"]) == (True, 0)


def test_a_date_read_off_the_receipt_is_kept() -> None:
    reading = {"transaction_date": "2026-10-03"}

    assert with_upload_date(reading, date(2026, 10, 9)) is reading


def test_a_failed_reading_is_left_alone() -> None:
    failed = {"error": "extraction_failed"}

    assert with_upload_date(failed, date(2026, 10, 9)) is failed
