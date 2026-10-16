"""Sending letters to users (F17.8.1)."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Letter:
    """One letter to one address: plain text, as every mail client reads it.

    `reply_to` is where a reply goes instead of the sender: the user who wrote through the
    contact form (F17.10.2), since letters leave from an address nobody reads.
    """

    to: str
    subject: str
    body: str
    reply_to: str | None = None


class EmailSendError(Exception):
    """The letter could not be handed over for delivery; worth trying again later."""


class EmailSenderPort(Protocol):
    """Hands a letter over for delivery (ADR-0019).

    Raises EmailSendError when it could not; never anything else, so the caller's retry
    loop is the same whichever provider is behind the port.
    """

    async def send(self, letter: Letter) -> None: ...
