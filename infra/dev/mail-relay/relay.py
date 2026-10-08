"""Local stand-in for the production inbound mail relay (F11.2, ADR-0013).

Listens for SMTP on port 2525 and hands every message, as received, to the
backend's intake webhook: exactly what the App Engine mail receiver does in
production with mail for `*@<project>.appspotmail.com`. Development only.
"""

import asyncio
import logging
import os
import threading
import urllib.error
import urllib.request

from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP, Envelope, Session

WEBHOOK_URL = os.environ.get(
    "INBOUND_WEBHOOK_URL", "http://backend:8000/api/v1/webhooks/inbound-email"
)
SECRET = os.environ["INBOUND_EMAIL_SECRET"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s mail-relay %(message)s")
log = logging.getLogger(__name__)


def _post(raw: bytes, recipient: str) -> str:
    request = urllib.request.Request(
        WEBHOOK_URL,
        data=raw,
        method="POST",
        headers={
            "Content-Type": "message/rfc822",
            "X-Inbound-Secret": SECRET,
            "X-Inbound-Recipient": recipient,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return f"{response.status} {response.read().decode()}"
    except urllib.error.HTTPError as error:
        return f"{error.code} {error.read().decode()}"


class Relay:
    async def handle_DATA(self, server: SMTP, session: Session, envelope: Envelope) -> str:
        raw = envelope.original_content or b""
        for recipient in envelope.rcpt_tos:
            result = await asyncio.to_thread(_post, raw, recipient)
            log.info("%s -> %s: %s", envelope.mail_from, recipient, result)
        return "250 Message accepted for delivery"


if __name__ == "__main__":
    controller = Controller(Relay(), hostname="0.0.0.0", port=2525)
    controller.start()
    log.info("listening on :2525, forwarding to %s", WEBHOOK_URL)
    threading.Event().wait()
