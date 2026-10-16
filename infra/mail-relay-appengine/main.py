"""Mail relay on App Engine: receipts in (F0.9.4, ADR-0013), account letters out (ADR-0019).

App Engine delivers every message sent to `*@<project>.appspotmail.com` as a POST to
`/_ah/mail/<address>`. This hands it, unchanged, to the backend's intake webhook with
the shared secret — the same contract as `infra/dev/mail-relay/relay.py` locally. It
decides nothing: the backend does all the checking.

The other way, `/send` takes a letter the backend wrote — with an optional reply-to, for
the contact form — and gives it to the Mail API, which only App Engine can call; the same
shared secret proves the backend sent it.
"""

import hmac
import logging
import os
import urllib.error
import urllib.request

from flask import Flask, request
from google.appengine.api import mail, wrap_wsgi_app

app = Flask(__name__)
app.wsgi_app = wrap_wsgi_app(app.wsgi_app)  # type: ignore[method-assign]

WEBHOOK_URL = os.environ["INBOUND_WEBHOOK_URL"]
SECRET = os.environ["INBOUND_EMAIL_SECRET"]
SENDER = f"Budget Agent <noreply@{os.environ['GOOGLE_CLOUD_PROJECT']}.appspotmail.com>"


@app.post("/_ah/mail/<path:address>")
def receive(address: str) -> tuple[str, int]:
    relay = urllib.request.Request(
        WEBHOOK_URL,
        data=request.get_data(),
        method="POST",
        headers={
            "Content-Type": "message/rfc822",
            "X-Inbound-Secret": SECRET,
            "X-Inbound-Recipient": address,
        },
    )
    try:
        with urllib.request.urlopen(relay, timeout=60) as response:
            logging.info("Relayed mail for %s: %s", address, response.status)
    except urllib.error.HTTPError as error:
        # A refusal is final; answering 200 stops App Engine retrying a message
        # the backend will never accept.
        logging.warning("Backend refused mail for %s: %s", address, error.code)
    return "", 200


@app.post("/send")
def send() -> tuple[str, int]:
    """Send one plain-text letter; 403 without the secret, 400 for an incomplete one.

    A Mail API failure is left to raise: the 500 tells the backend to try again.
    """
    if not hmac.compare_digest(request.headers.get("X-Relay-Secret", ""), SECRET):
        return "", 403
    letter = request.get_json(silent=True) or {}
    to, subject, body = (letter.get(key) for key in ("to", "subject", "body"))
    if not all(isinstance(value, str) and value for value in (to, subject, body)):
        return "", 400
    reply_to = letter.get("reply_to")
    extra = {"reply_to": reply_to} if isinstance(reply_to, str) and reply_to else {}
    mail.send_mail(sender=SENDER, to=to, subject=subject, body=body, **extra)
    logging.info("Sent %r", subject)
    return "", 202
