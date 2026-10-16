"""What the service writes to its users (F17.8.1)."""

import pytest

from app.domain.letters import LANGUAGES, WORDING, LetterKind, write_letter


@pytest.mark.parametrize("kind", list(LetterKind))
def test_every_letter_is_written_in_every_language(kind: LetterKind) -> None:
    assert set(WORDING[kind]) == set(LANGUAGES)


def test_a_letter_carries_the_name_and_the_link_in_the_readers_language() -> None:
    letter = write_letter(LetterKind.CONFIRM_EMAIL, "uk", name="Оля", link="https://x/y")

    assert letter.subject == "Підтвердіть адресу пошти"
    assert "Оля" in letter.body and "https://x/y" in letter.body


def test_a_reader_whose_language_is_unknown_gets_english() -> None:
    assert write_letter(LetterKind.RESET_PASSWORD, None, name="A").subject == "Reset your password"
    assert write_letter(LetterKind.RESET_PASSWORD, "de", name="A").subject == "Reset your password"
