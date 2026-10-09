"""What a new password must have (BRD G1)."""

from app.domain.passwords import password_problems


def test_a_password_with_a_letter_a_digit_and_a_symbol_is_accepted() -> None:
    assert password_problems("Kawa-2026") == []


def test_each_missing_rule_is_named() -> None:
    assert password_problems("abc") == [
        "at least 8 characters",
        "a digit",
        "a special character such as @, ! or #",
    ]
    assert password_problems("12345678!") == ["a letter"]


def test_a_common_password_is_refused_even_when_it_meets_the_rules() -> None:
    assert password_problems("Password123") == [
        "a special character such as @, ! or #",
        "not to be a common password",
    ]
