"""Writing to the people running the service (F17.10.2)."""

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import StrEnum

from app.api.errors import AppError, ProblemCode
from app.domain.letters import LetterKind, write_letter
from app.ports.email import Letter

MESSAGES_PER_ADDRESS = 3
"""Messages one reply address may send per window, on top of the per-IP limit."""
ADDRESS_WINDOW_SECONDS = 24 * 60 * 60


class ContactTopic(StrEnum):
    """What a message is about, so it can be answered by the right person first."""

    QUESTION = "question"
    PROBLEM = "problem"
    IDEA = "idea"
    DATA = "data"
    """A request about one's personal data (GDPR art. 15-22)."""


class TooManyMessagesError(AppError):
    """One reply address wrote more often than a person would (F17.10.2)."""

    status_code = 429
    code = ProblemCode.RATE_LIMITED
    title = "Too Many Requests"


class AddressThrottle:
    """Counts messages per reply address over a sliding window, in this process's memory.

    Like the per-IP limits (app/api/rate_limit.py): with at most two instances an address
    gets at most twice the limit, enough to stop a script without a shared store.
    """

    def __init__(
        self, limit: int = MESSAGES_PER_ADDRESS, window: float = ADDRESS_WINDOW_SECONDS
    ) -> None:
        self.limit = limit
        self.window = window
        self.sent: defaultdict[str, deque[float]] = defaultdict(deque)

    def admit(self, address: str, now: float | None = None) -> None:
        """Count one more message from `address`, or raise TooManyMessagesError."""
        moment = time.monotonic() if now is None else now
        times = self.sent[address.lower()]
        while times and moment - times[0] > self.window:
            times.popleft()
        if len(times) >= self.limit:
            retry = int(self.window - (moment - times[0])) + 1
            raise TooManyMessagesError(
                f"Too many messages from this address. Try again in {retry} seconds.",
                params={"seconds": retry},
            )
        times.append(moment)


THROTTLE = AddressThrottle()


@dataclass(frozen=True)
class ContactMessage:
    """What a visitor wrote, and where to answer them."""

    email: str
    topic: ContactTopic
    message: str
    language: str | None


def contact_letters(message: ContactMessage, admins: list[str]) -> list[Letter]:
    """The message for each administrator, answerable by reply, and the sender's copy.

    No administrator configured, the sender still gets the copy and the message is in
    the log (LogMailSender locally), so a missing setting never loses it silently.
    """
    to_admins = [
        Letter(
            to=admin,
            subject=f"[Budget Agent] {message.topic.value}: {message.email}",
            body=f"From: {message.email}\nTopic: {message.topic.value}\n"
            f"Language: {message.language or 'unknown'}\n\n{message.message}",
            reply_to=message.email,
        )
        for admin in admins
    ]
    copy = write_letter(LetterKind.CONTACT_RECEIVED, message.language, message=message.message)
    return [*to_admins, Letter(message.email, copy.subject, copy.body)]
