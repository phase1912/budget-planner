"""Per-client-IP limits on the endpoints that are expensive or invite abuse (F10.6.3).

Keyed on the client address, which Cloud Run passes in X-Forwarded-For and uvicorn
unwraps (`--proxy-headers`, backend/Dockerfile.prod). Counted in memory per instance:
with at most two instances a client gets at most twice the limit, which is enough to
stop scripted abuse without a shared store.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

LOGIN = "5/minute"
"""Password guessing (G2)."""
REGISTER = "3/hour"
"""Accounts made in bulk to get round the per-account receipt quota."""
UPLOAD = "10/minute"
"""Each upload starts model calls; a person photographing receipts never gets near it."""
ADVICE = "10/minute"
"""Each ask is a model call."""
EXPORT = "5/minute"
"""Each export writes a file of the whole history in the background."""

JOIN = "10/minute"
"""Reading and using invite links: codes are unguessable, this only stops scripted probing.

Applied as one shared limit, not per route: the limiter keys routes by URL, and every code
is a different URL, so a per-route limit would never be reached by trying codes."""
