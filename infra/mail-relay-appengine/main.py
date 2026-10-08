"""Inbound mail relay on App Engine (F0.9.4, ADR-0013).

App Engine delivers every message sent to `*@<project>.appspotmail.com` as a POST to
`/_ah/mail/<address>`. This hands it, unchanged, to the backend's intake webhook with
the shared secret — the same contract as `infra/dev/mail-relay/relay.py` locally. It
decides nothing: the backend does all the checking.
"""

import logging
import os
import urllib.error
import urllib.request

from flask import Flask, request
from google.appengine.api import wrap_wsgi_app

app = Flask(__name__)
app.wsgi_app = wrap_wsgi_app(app.wsgi_app)  # type: ignore[method-assign]

WEBHOOK_URL = os.environ["INBOUND_WEBHOOK_URL"]
SECRET = os.environ["INBOUND_EMAIL_SECRET"]


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
