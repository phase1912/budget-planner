"""Ways letters leave the service (F17.8.1, ADR-0019)."""

import logging

import httpx

from app.ports.email import EmailSendError, Letter

logger = logging.getLogger(__name__)


class AppEngineMailSender:
    """Sends through the App Engine mail relay's `/send`, which calls the Mail API.

    The Mail API is only reachable from inside App Engine, so the relay that already
    receives forwarded receipts also sends, authenticated by the same shared secret.
    """

    def __init__(self, url: str, secret: str, timeout: float = 15.0) -> None:
        self.url = url
        self.secret = secret
        self.timeout = timeout

    async def send(self, letter: Letter) -> None:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.url,
                    json={"to": letter.to, "subject": letter.subject, "body": letter.body},
                    headers={"X-Relay-Secret": self.secret},
                )
        except httpx.HTTPError as error:
            raise EmailSendError(f"Mail relay unreachable: {error}") from error
        if response.status_code >= 300:
            raise EmailSendError(f"Mail relay answered {response.status_code}")


class LogMailSender:
    """Writes letters to the log instead of sending them: local work and demos.

    A developer signing up locally finds the confirmation link in the backend's output.
    """

    async def send(self, letter: Letter) -> None:
        logger.warning("Letter to %s — %s\n%s", letter.to, letter.subject, letter.body)
