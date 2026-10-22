"""A month's AI credits against an account's plan (F10.6, F21.9): spent by what calls cost,
shown as receipts and messages left."""

from datetime import date
from decimal import Decimal

from app.domain.quota import CreditWallet, next_month_start, speech_credits

RENEWS = date(2026, 11, 1)


def wallet(limit: int | None, used: str) -> CreditWallet:
    return CreditWallet(
        limit=limit,
        used=Decimal(used),
        resets_on=RENEWS,
        per_receipt=Decimal("10"),
        per_message=Decimal("4"),
    )


def test_the_wallet_renews_on_the_first_of_next_month_even_across_a_year() -> None:
    assert next_month_start(date(2026, 10, 8)) == date(2026, 11, 1)
    assert next_month_start(date(2026, 12, 31)) == date(2027, 1, 1)


def test_what_is_left_is_told_as_receipts_and_as_messages() -> None:
    free = wallet(150, "42.5")

    assert free.remaining == Decimal("107.5")
    assert (free.receipts_left, free.messages_left) == (10, 26)


def test_spending_is_allowed_up_to_what_is_left_and_not_past_it() -> None:
    free = wallet(150, "140")

    assert (free.allows(Decimal("10")), free.allows(Decimal("10.001"))) == (True, False)


def test_an_account_without_a_limit_is_never_refused() -> None:
    admin = wallet(None, "9000")

    assert (admin.unlimited, admin.remaining, admin.allows(Decimal("1000000"))) == (
        True,
        None,
        True,
    )
    assert (admin.receipts_left, admin.messages_left) == (None, None)


def test_what_is_left_never_goes_below_zero() -> None:
    over = wallet(150, "151.2")

    assert (over.remaining, over.receipts_left, over.messages_left) == (Decimal(0), 0, 0)


def test_a_minute_of_speech_costs_what_speech_to_text_charges() -> None:
    assert speech_credits(Decimal(60)) == Decimal("16.000")
    assert speech_credits(Decimal("7.5")) == Decimal("2.000")
