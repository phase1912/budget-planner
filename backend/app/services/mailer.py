"""Delivering letters without ever failing the request that wrote them (F17.8.1)."""

import asyncio
import logging
from collections.abc import Sequence

from app.ports.email import EmailSenderPort, EmailSendError, Letter

logger = logging.getLogger(__name__)

RETRY_DELAYS: Sequence[float] = (2.0, 10.0, 30.0)
"""Seconds to wait before each further attempt: a relay cold start takes about 20."""


class Mailer:
    """Hands letters to the sender, trying again on failure, in the background.

    Run after the response has gone (FastAPI background tasks): the user is told the
    letter is on its way, and a failure that outlasts every retry is logged, not
    reported — the screen offers to send it again.
    """

    def __init__(self, sender: EmailSenderPort, delays: Sequence[float] = RETRY_DELAYS) -> None:
        self.sender = sender
        self.delays = delays

    async def deliver(self, letter: Letter) -> bool:
        """Send `letter`, retrying; True once it is handed over, False after giving up."""
        for attempt, delay in enumerate([0.0, *self.delays], start=1):
            if delay:
                await asyncio.sleep(delay)
            try:
                await self.sender.send(letter)
                return True
            except EmailSendError as error:
                logger.warning("Letter %r, attempt %d failed: %s", letter.subject, attempt, error)
        logger.error("Letter %r to a user was not sent after every retry", letter.subject)
        return False
