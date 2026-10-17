"""What the service counts about its own use, and how (F17.3).

Signed-in users' actions are recorded against their account, for running and supporting
the service (legitimate interest, ADR-0020); visits to the public pages are only counted,
by page and source, with nothing that could say who.
"""

import re
from datetime import timedelta
from enum import StrEnum
from typing import Final
from urllib.parse import urlparse

ACTIVITY_RETENTION: Final = timedelta(days=365)
"""How long one user's activity is kept; older events are pruned (ADR-0020)."""


class ActivityKind(StrEnum):
    """The actions recorded for a signed-in user (F17.3.1)."""

    SIGNED_UP = "signed_up"
    EMAIL_CONFIRMED = "email_confirmed"
    SIGNED_IN = "signed_in"
    ACTIVE = "active"
    """The first request of a day: what weekly and monthly active users are counted from."""
    RECEIPT_UPLOADED = "receipt_uploaded"
    RECEIPT_STORED = "receipt_stored"
    EXPORTED = "exported"


PUBLIC_PAGES: Final = frozenset(
    {"/", "/en", "/uk", "/pl", "/help", "/privacy", "/terms", "/login", "/register"}
)
"""The pages whose visits are counted; any other path is not a public page."""

DIRECT: Final = "direct"

KNOWN_SOURCES: Final = {
    "instagram": ("instagram.com", "l.instagram.com", "lm.instagram.com", "com.instagram.android"),
    "facebook": (
        "facebook.com",
        "m.facebook.com",
        "l.facebook.com",
        "lm.facebook.com",
        "fb.com",
        "fb.me",
        "com.facebook.katana",
    ),
    "x": ("t.co", "x.com", "twitter.com", "mobile.twitter.com"),
    "telegram": ("t.me", "web.telegram.org", "org.telegram.messenger"),
    "linkedin": ("linkedin.com", "lnkd.in", "com.linkedin.android"),
    "youtube": ("youtube.com", "m.youtube.com", "youtu.be"),
    "reddit": ("reddit.com", "old.reddit.com", "out.reddit.com"),
    "tiktok": ("tiktok.com", "vm.tiktok.com"),
}
"""Sites and apps that refer under several addresses — link shims, mobile hosts, apps'
package names — each counted under one name, so Instagram is one row, not three."""
_HOST_TO_SOURCE: Final = {host: name for name, hosts in KNOWN_SOURCES.items() for host in hosts}
_SEARCH = re.compile(r"^(?:[a-z]+\.)?(google|bing|duckduckgo|yahoo|yandex|ecosia)\.[a-z.]+$")
_SOURCE = re.compile(r"[^a-z0-9.\-_]")
_BOTS = re.compile(
    r"bot|crawl|spider|slurp|preview|headless|lighthouse|facebookexternalhit|curl|wget|python",
    re.IGNORECASE,
)


def visit_source(referrer: str | None, utm_source: str | None, own_host: str) -> str:
    """Where a visit came from: the campaign it names, else the referring site, else direct.

    A site known under several addresses is named once (`KNOWN_SOURCES`), and a search
    engine by its name whatever its country domain (google.pl, google.com → google).

    Only a domain or a short campaign name is kept — never a full address, which could
    carry a search or a person's page.
    """
    if utm_source and (campaign := _SOURCE.sub("", utm_source.lower())[:64]):
        return campaign
    host = (urlparse(referrer).hostname or "") if referrer else ""
    host = host.lower().removeprefix("www.")
    if not host or host == own_host.lower().removeprefix("www."):
        return DIRECT
    if host in _HOST_TO_SOURCE:
        return _HOST_TO_SOURCE[host]
    if search := _SEARCH.match(host):
        return search.group(1)
    return host[:64]


def is_bot(user_agent: str | None) -> bool:
    """Whether a visit was a crawler or a tool rather than a person's browser."""
    return not user_agent or bool(_BOTS.search(user_agent))
