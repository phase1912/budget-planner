from typing import Protocol


class SpeechUnavailable(Exception):
    """The recogniser could not be reached or gave no answer; the user can type instead."""


class SpeechPort(Protocol):
    """Turns a short recording into the words said (F21.2.2, ADR-0031).

    The recording is recognised and dropped: nothing of the sound is kept. `language` is
    the user's; what was said in another of the product's languages must still come back
    as said, so an adapter tells the language by the sound rather than trusting it.
    Returns "" for silence. Raises SpeechUnavailable when the recogniser fails, so the
    microphone says so instead of sending nothing.
    """

    async def recognise(self, audio: bytes, mime_type: str, language: str) -> str: ...
