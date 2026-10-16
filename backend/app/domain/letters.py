"""What the service writes to its users, in their language (F17.8).

Plain text only: every mail client shows it, and a link in it is the whole point of
each letter. The wording is kept here, beside the other rules about accounts, rather
than in templates, so a missing translation is a failing test, not a blank letter.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class LetterKind(StrEnum):
    """Why the service writes."""

    CONFIRM_EMAIL = "confirm_email"
    RESET_PASSWORD = "reset_password"
    CHANGE_EMAIL = "change_email"
    EMAIL_CHANGED = "email_changed"


@dataclass(frozen=True)
class Wording:
    """A letter's subject and body; the body may name `{name}`, `{link}` and `{email}`."""

    subject: str
    body: str


LANGUAGES: Final = ("en", "uk", "pl")
SIGNATURE: Final = {"en": "— Budget Agent", "uk": "— Budget Agent", "pl": "— Budget Agent"}

WORDING: Final[dict[LetterKind, dict[str, Wording]]] = {
    LetterKind.CONFIRM_EMAIL: {
        "en": Wording(
            "Confirm your email address",
            "Hello {name},\n\nConfirm this is your address to start adding receipts:\n\n"
            "{link}\n\nThe link works for 24 hours. If you did not sign up, ignore this "
            "letter and nothing happens.",
        ),
        "uk": Wording(
            "Підтвердіть адресу пошти",
            "Вітаємо, {name}!\n\nПідтвердіть, що це ваша адреса, щоб почати додавати "
            "чеки:\n\n{link}\n\nПосилання діє 24 години. Якщо ви не реєструвалися, просто "
            "проігноруйте цей лист.",
        ),
        "pl": Wording(
            "Potwierdź adres e-mail",
            "Dzień dobry, {name}!\n\nPotwierdź, że to Twój adres, aby zacząć dodawać "
            "paragony:\n\n{link}\n\nLink działa przez 24 godziny. Jeśli to nie Ty zakładałeś "
            "konto, zignoruj tę wiadomość.",
        ),
    },
    LetterKind.RESET_PASSWORD: {
        "en": Wording(
            "Reset your password",
            "Hello {name},\n\nSomeone asked to reset the password of your account. To set a "
            "new one, open:\n\n{link}\n\nThe link works for one hour and only once. If it "
            "was not you, ignore this letter: your password stays as it is.",
        ),
        "uk": Wording(
            "Скидання пароля",
            "Вітаємо, {name}!\n\nХтось попросив скинути пароль вашого облікового запису. "
            "Щоб задати новий, відкрийте:\n\n{link}\n\nПосилання діє одну годину і лише "
            "один раз. Якщо це були не ви, проігноруйте лист: пароль не зміниться.",
        ),
        "pl": Wording(
            "Resetowanie hasła",
            "Dzień dobry, {name}!\n\nKtoś poprosił o zresetowanie hasła do Twojego konta. "
            "Aby ustawić nowe, otwórz:\n\n{link}\n\nLink działa przez godzinę i tylko raz. "
            "Jeśli to nie Ty, zignoruj tę wiadomość: hasło się nie zmieni.",
        ),
    },
    LetterKind.CHANGE_EMAIL: {
        "en": Wording(
            "Confirm your new email address",
            "Hello {name},\n\nYou asked to sign in with this address from now on. Confirm "
            "it to make the change:\n\n{link}\n\nThe link works for 24 hours. Until then "
            "your account keeps its current address.",
        ),
        "uk": Wording(
            "Підтвердіть нову адресу пошти",
            "Вітаємо, {name}!\n\nВи попросили надалі входити з цією адресою. Підтвердіть "
            "її, щоб завершити зміну:\n\n{link}\n\nПосилання діє 24 години. До того "
            "обліковий запис залишається з попередньою адресою.",
        ),
        "pl": Wording(
            "Potwierdź nowy adres e-mail",
            "Dzień dobry, {name}!\n\nPoprosiłeś o logowanie od teraz tym adresem. Potwierdź "
            "go, aby dokończyć zmianę:\n\n{link}\n\nLink działa przez 24 godziny. Do tego "
            "czasu konto zachowuje obecny adres.",
        ),
    },
    LetterKind.EMAIL_CHANGED: {
        "en": Wording(
            "Your email address was changed",
            "Hello {name},\n\nYour account now signs in with {email} instead of this "
            "address. If this was not you, sign in at once, set your own address back and "
            "change your password.",
        ),
        "uk": Wording(
            "Адресу пошти змінено",
            "Вітаємо, {name}!\n\nВаш обліковий запис тепер входить з адресою {email} "
            "замість цієї. Якщо це були не ви, негайно увійдіть, поверніть свою адресу і "
            "змініть пароль.",
        ),
        "pl": Wording(
            "Adres e-mail został zmieniony",
            "Dzień dobry, {name}!\n\nTwoje konto loguje się teraz adresem {email} zamiast "
            "tego. Jeśli to nie Ty, natychmiast się zaloguj, przywróć swój adres i zmień "
            "hasło.",
        ),
    },
}


def write_letter(
    kind: LetterKind, language: str | None, *, name: str, link: str = "", email: str = ""
) -> Wording:
    """The letter of this kind in the reader's language, English when it is unknown."""
    chosen = language if language in LANGUAGES else "en"
    wording = WORDING[kind][chosen]
    body = wording.body.format(name=name, link=link, email=email)
    return Wording(wording.subject, f"{body}\n\n{SIGNATURE[chosen]}")
