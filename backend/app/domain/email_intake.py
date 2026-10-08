"""Receipts that arrive by email (F11.2): forwarding addresses and inbound messages.

A user forwards an e-receipt to their own address, `receipts-<token>@<domain>`.
The token is the only secret in it, so it is long, random and replaceable; the
domain comes from configuration, because where mail lands is a deployment
decision (ADR-0013), not a property of the user.
"""

import secrets
from dataclasses import dataclass, field
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import parseaddr
from html.parser import HTMLParser

ADDRESS_PREFIX = "receipts-"

READABLE_ATTACHMENTS = frozenset(
    {"application/pdf", "image/jpeg", "image/png", "image/heic", "image/heif"}
)
"""Attachment types the receipt parser can read; anything else in a message is ignored."""


def new_forwarding_token() -> str:
    """A fresh, unguessable token for a forwarding address (64 random bits)."""
    return secrets.token_hex(8)


def forwarding_address(token: str, domain: str) -> str:
    """The address a user forwards receipts to."""
    return f"{ADDRESS_PREFIX}{token}@{domain}"


def token_from_address(address: str, domain: str) -> str | None:
    """The token in a forwarding address on `domain`, or None if it is not one."""
    local, _, at = parseaddr(address)[1].lower().rpartition("@")
    if at != domain.lower() or not local.startswith(ADDRESS_PREFIX):
        return None
    return local.removeprefix(ADDRESS_PREFIX) or None


@dataclass(frozen=True)
class Attachment:
    """One readable file attached to an inbound message."""

    content_type: str
    content: bytes


@dataclass(frozen=True)
class InboundEmail:
    """What intake needs from one received message.

    `sender` is the bare address in From; `message_id` identifies the message,
    so a relay that delivers it twice does not make two receipts. `text` is the
    readable body, HTML reduced to its words.
    """

    sender: str
    message_id: str | None
    subject: str
    text: str
    attachments: list[Attachment] = field(default_factory=list)


def parse_message(raw: bytes) -> InboundEmail:
    """Read a raw RFC 5322 message into what intake needs.

    Only attachments in READABLE_ATTACHMENTS are kept. The body prefers HTML,
    since that is how shops send e-receipts, and falls back to plain text.
    """
    message = BytesParser(policy=policy.default).parsebytes(raw)
    assert isinstance(message, EmailMessage)
    attachments = [
        Attachment(part.get_content_type(), part.get_content())
        for part in message.iter_attachments()
        if isinstance(part, EmailMessage) and part.get_content_type() in READABLE_ATTACHMENTS
    ]
    body = message.get_body(preferencelist=("html", "plain"))
    text = ""
    if body is not None:
        content = body.get_content()
        text = html_to_text(content) if body.get_content_type() == "text/html" else content
    return InboundEmail(
        sender=parseaddr(str(message.get("From", "")))[1].lower(),
        message_id=str(message["Message-ID"]).strip() if message["Message-ID"] else None,
        subject=str(message.get("Subject", "")),
        text=text.strip(),
        attachments=attachments,
    )


class _TextExtractor(HTMLParser):
    _SKIPPED = frozenset({"script", "style", "head", "title"})
    _BREAKS = frozenset({"br", "p", "div", "tr", "li", "table", "h1", "h2", "h3"})

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skipping = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._SKIPPED:
            self._skipping += 1
        elif tag in self._BREAKS:
            self.parts.append("\n")
        elif tag == "td":
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIPPED and self._skipping:
            self._skipping -= 1

    def handle_data(self, data: str) -> None:
        if not self._skipping:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    """The words of an HTML e-receipt, one table row or paragraph per line.

    Markup, styles and scripts would cost the model tokens and carry nothing a
    receipt needs; what is left keeps the row structure prices depend on.
    """
    extractor = _TextExtractor()
    extractor.feed(html)
    lines = (" ".join(line.split()) for line in "".join(extractor.parts).splitlines())
    return "\n".join(line for line in lines if line)
