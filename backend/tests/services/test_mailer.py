"""Letters are retried, and a failure never reaches the user's request (F17.8.1)."""

import pytest

from app.ports.email import EmailSendError, Letter
from app.services.mailer import Mailer

LETTER = Letter("a@example.com", "Hello", "Body")


class FlakySender:
    """Fails `failures` times, then accepts; records what it accepted."""

    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.sent: list[Letter] = []

    async def send(self, letter: Letter) -> None:
        if self.failures:
            self.failures -= 1
            raise EmailSendError("relay down")
        self.sent.append(letter)


@pytest.mark.asyncio
async def test_a_letter_that_failed_is_tried_again_until_it_goes() -> None:
    sender = FlakySender(failures=2)

    assert await Mailer(sender, delays=(0, 0, 0)).deliver(LETTER)
    assert sender.sent == [LETTER]


@pytest.mark.asyncio
async def test_after_every_retry_failed_the_letter_is_given_up_without_raising() -> None:
    sender = FlakySender(failures=10)

    assert not await Mailer(sender, delays=(0, 0)).deliver(LETTER)
    assert sender.sent == []
