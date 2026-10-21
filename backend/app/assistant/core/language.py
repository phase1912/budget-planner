"""Which language a message is written in, told by its letters (F21.1).

A small model asked to "answer in the user's language" still drifts to the language of its
examples; told the language by name, it keeps to it. Only the languages the product speaks
and its neighbours are told apart; anything else is left to the profile's language.
"""

import re

UKRAINIAN = re.compile(r"[іїєґ]", re.IGNORECASE)
RUSSIAN = re.compile(r"[ыэъё]", re.IGNORECASE)
CYRILLIC = re.compile(r"[\u0400-\u04ff]")
POLISH = re.compile(r"[ąćęłńśźż]", re.IGNORECASE)
POLISH_WORDS = re.compile(
    r"\b(jest|się|nie|na|ile|wydał\w*|moj\w*|mój|czy|proszę|dzięki|budżet|miesiąc\w*)\b",
    re.IGNORECASE,
)
LATIN = re.compile(r"[a-z]", re.IGNORECASE)
RUSSIAN_WORDS = re.compile(
    r"(?<![\w])(что|как|сколько|можешь|поменя\w*|потрат\w*|месяц\w*|мне|меня|мой|моя|"
    r"это|пожалуйста|спасибо|привет|сделай|добавь|какой|какая|какие|"
    r"сегодня|вчера|где|деньги)(?![\w])",
    re.IGNORECASE,
)


def language_of(text: str, fallback: str) -> str:
    """The language `text` is written in, as an English name; `fallback` when its letters
    do not tell. Cyrillic with no letter only one of the languages has is Russian when it
    uses words only Russian does, else Ukrainian, the product's own."""
    if UKRAINIAN.search(text):
        return "Ukrainian"
    if RUSSIAN.search(text):
        return "Russian"
    if CYRILLIC.search(text):
        # Neither alphabet's own letters: words only Russian uses tell it apart.
        return "Russian" if RUSSIAN_WORDS.search(text) or fallback == "Russian" else "Ukrainian"
    if POLISH.search(text) or POLISH_WORDS.search(text):
        return "Polish"
    if LATIN.search(text):
        return "English"
    return fallback
