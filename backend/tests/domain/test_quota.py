"""A month's receipt reads against an account's limit (F10.6)."""

from datetime import date

from app.domain.quota import ReceiptQuota, next_month_start


def test_the_quota_resets_on_the_first_of_next_month_even_across_a_year() -> None:
    assert next_month_start(date(2026, 10, 8)) == date(2026, 11, 1)
    assert next_month_start(date(2026, 12, 31)) == date(2027, 1, 1)


def test_reads_are_allowed_up_to_the_limit_and_not_past_it() -> None:
    quota = ReceiptQuota(limit=10, used=8, resets_on=date(2026, 11, 1))

    assert (quota.remaining, quota.allows(2), quota.allows(3)) == (2, True, False)


def test_an_account_without_a_limit_is_never_refused() -> None:
    quota = ReceiptQuota(limit=None, used=500, resets_on=date(2026, 11, 1))

    assert (quota.unlimited, quota.remaining, quota.allows(1000)) == (True, None, True)


def test_remaining_never_goes_below_zero() -> None:
    assert ReceiptQuota(limit=10, used=12, resets_on=date(2026, 11, 1)).remaining == 0
