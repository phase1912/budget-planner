"""Per-client-IP limits on the endpoints that are expensive or invite abuse (F10.6.3).

Keyed on the client address, which Cloud Run passes in X-Forwarded-For and uvicorn
unwraps (`--proxy-headers`, backend/Dockerfile.prod). Counted in memory per instance:
with at most two instances a client gets at most twice the limit, which is enough to
stop scripted abuse without a shared store.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

# Off only for the browser suite on the local stack (F0.11.1); Settings refuses it elsewhere.
limiter = Limiter(key_func=get_remote_address, enabled=get_settings().rate_limits_enabled)

LOGIN = "5/minute"
"""Password guessing (G2)."""
REGISTER = "3/hour"
"""Accounts made in bulk to get round the per-account receipt quota."""
ACCOUNT_LETTER = "5/hour"
"""Letters a client may have sent to an address: each lands in someone's inbox (F17.8)."""
CONTACT = "5/hour"
"""Messages through the contact form from one client (F17.10.2)."""
PAGE_VIEWS = "60/minute"
"""Page views counted from one client: a person reads far fewer; a script stops here."""
UPLOAD = "10/minute"
"""Each upload starts model calls; a person photographing receipts never gets near it."""
ASSISTANT = "20/minute"
"""Each message to the assistant is a model call; a person talking never gets near it."""
SPEECH = "20/minute"
"""Each recording is recognised by Google Cloud (F21.2.2); as many as messages."""
ADVICE = "10/minute"
"""Each ask is a model call."""
EXPORT = "5/minute"
"""Each export writes a file of the whole history in the background."""

JOIN = "10/minute"
"""Reading and using invite links: codes are unguessable, this only stops scripted probing.

Applied as one shared limit, not per route: the limiter keys routes by URL, and every code
is a different URL, so a per-route limit would never be reached by trying codes."""
