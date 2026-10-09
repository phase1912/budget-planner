"""Receipts forwarded by email, over HTTP from the inbound mail relay (F11.2, BRD N2)."""

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from email.message import EmailMessage
from typing import Any
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient, Response
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.email_ingestion import EmailIngestionAdapter
from app.api.routers.webhooks import get_email_ingestion
from app.core.config import get_settings
from app.db.session import get_db_session
from app.domain.email_intake import forwarding_address
from app.main import create_app
from app.models.line_item import LineItem
from app.models.receipt import Receipt, ReceiptChannel, ReceiptStatus
from app.models.user import User
from app.ports.storage import receipt_object_name
from app.schemas.extraction import ExtractedLineItem, ExtractedReceipt
from tests.factories.user import UserFactory

SECRET = "relay-secret"
DOMAIN = "inbound.test"


class StubParser:
    """Stands in for the vision model: reads every message as the same two-line receipt."""

    def __init__(self) -> None:
        self.read: list[tuple[list[bytes], list[str] | None]] = []

    async def parse(
        self, images: list[bytes], *, mime_types: list[str] | None = None
    ) -> ExtractedReceipt:
        self.read.append((images, mime_types))
        return ExtractedReceipt(
            merchant_name="Żabka",
            transaction_date="2026-10-08",
            receipt_total="12.50",
            items_sum_matches_total=True,
            line_items=[
                ExtractedLineItem(name="Woda", quantity="1", unit_price="2.50", total_price="2.50"),
                ExtractedLineItem(
                    name="Kawa", quantity="1", unit_price="10.00", total_price="10.00"
                ),
            ],
        )


class RecordingStorage:
    def __init__(self) -> None:
        self.uploaded: list[str] = []

    async def upload_file(
        self,
        object_name: str,
        content: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> str:
        self.uploaded.append(object_name)
        return object_name


@pytest.fixture(autouse=True)
def relay_settings() -> Iterator[None]:
    settings = get_settings()
    with (
        patch.object(settings, "inbound_email_secret", SecretStr(SECRET)),
        patch.object(settings, "inbound_email_domain", DOMAIN),
        patch.object(settings, "inbound_email_daily_limit", 2),
    ):
        yield


def _message(sender: str, *, html: str = "", pdf: bytes | None = None, msg_id: str = "") -> bytes:
    message = EmailMessage()
    message["From"] = f"Shopper <{sender}>"
    message["To"] = "someone@example.com"
    message["Subject"] = "Fwd: Twój paragon"
    message["Message-ID"] = msg_id or "<receipt-1@shop.example>"
    message.set_content("See the receipt below.")
    if html:
        message.add_alternative(html, subtype="html")
    if pdf is not None:
        message.add_attachment(pdf, maintype="application", subtype="pdf", filename="r.pdf")
    return message.as_bytes()


async def _deliver(
    session: AsyncSession,
    to: str,
    raw: bytes,
    *,
    secret: str | None = SECRET,
    parser: StubParser | None = None,
    storage: RecordingStorage | None = None,
) -> Response:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield session

    @asynccontextmanager
    async def same_session() -> AsyncIterator[AsyncSession]:
        yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_email_ingestion] = lambda: EmailIngestionAdapter(
        storage or RecordingStorage(),  # type: ignore[arg-type]
        parser or StubParser(),
    )
    headers = {"X-Inbound-Recipient": to, "Content-Type": "message/rfc822"}
    if secret is not None:
        headers["X-Inbound-Secret"] = secret
    with patch("app.services.receipt.get_session_factory", return_value=same_session):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            return await client.post("/api/v1/webhooks/inbound-email", content=raw, headers=headers)


async def _receipts(session: AsyncSession, user: User) -> list[Receipt]:
    rows = await session.execute(select(Receipt).where(Receipt.user_id == user.id))
    return list(rows.scalars())


def _address(user: Any) -> str:
    return forwarding_address(user.forwarding_token, DOMAIN)


@pytest.mark.asyncio
async def test_a_forwarded_html_receipt_becomes_an_itemised_email_receipt(
    db_session: AsyncSession,
) -> None:
    """The F11.2 demo: forward an e-receipt from your own email and it is on Receipts."""
    owner = await UserFactory.create_async(email="shopper@example.com")
    parser = StubParser()
    html = "<html><style>td{color:red}</style><table><tr><td>Woda</td><td>2,50</td></tr></table>"

    response = await _deliver(
        db_session, _address(owner), _message("Shopper@Example.com", html=html), parser=parser
    )

    assert (response.status_code, response.json()["status"]) == (202, "accepted")
    [receipt] = await _receipts(db_session, owner)
    assert (receipt.channel, receipt.source_reference) == (
        ReceiptChannel.EMAIL,
        "<receipt-1@shop.example>",
    )
    assert receipt.status == ReceiptStatus.PARSED
    items = await db_session.execute(select(LineItem).where(LineItem.receipt_id == receipt.id))
    assert sorted(i.name for i in items.scalars()) == ["Kawa", "Woda"]
    [(contents, types)] = parser.read
    assert (contents, types) == ([b"Woda 2,50"], ["text/plain"])


@pytest.mark.asyncio
async def test_a_pdf_receipt_is_stored_under_its_owners_prefix_and_read(
    db_session: AsyncSession,
) -> None:
    owner = await UserFactory.create_async(email="shopper@example.com")
    storage, parser = RecordingStorage(), StubParser()

    await _deliver(
        db_session,
        _address(owner),
        _message("shopper@example.com", pdf=b"%PDF-1.4 receipt"),
        parser=parser,
        storage=storage,
    )

    [receipt] = await _receipts(db_session, owner)
    assert storage.uploaded == [receipt_object_name(owner.id, receipt.file_ids[0])]
    assert parser.read == [([b"%PDF-1.4 receipt"], ["application/pdf"])]


@pytest.mark.asyncio
async def test_mail_from_anyone_but_the_owner_is_dropped(db_session: AsyncSession) -> None:
    owner = await UserFactory.create_async(email="shopper@example.com")
    parser = StubParser()

    response = await _deliver(
        db_session,
        _address(owner),
        _message("stranger@example.com", html="<p>x</p>"),
        parser=parser,
    )

    assert response.json() == {"status": "dropped", "reason": "unverified_sender"}
    assert (await _receipts(db_session, owner), parser.read) == ([], [])


@pytest.mark.asyncio
async def test_one_users_address_never_writes_to_another_users_receipts(
    db_session: AsyncSession,
) -> None:
    """N2: mailing user A's address from user B's email puts nothing anywhere."""
    owner = await UserFactory.create_async(email="a@example.com")
    other = await UserFactory.create_async(email="b@example.com")

    response = await _deliver(
        db_session, _address(owner), _message("b@example.com", html="<p>x</p>")
    )

    assert response.json()["reason"] == "unverified_sender"
    assert await _receipts(db_session, owner) == []
    assert await _receipts(db_session, other) == []


@pytest.mark.asyncio
async def test_an_address_that_is_not_a_users_is_dropped(db_session: AsyncSession) -> None:
    await UserFactory.create_async(email="shopper@example.com")

    response = await _deliver(
        db_session, f"receipts-0000@{DOMAIN}", _message("shopper@example.com", html="<p>x</p>")
    )

    assert response.json() == {"status": "dropped", "reason": "unknown_recipient"}


@pytest.mark.asyncio
async def test_without_the_relays_secret_nothing_is_read(db_session: AsyncSession) -> None:
    owner = await UserFactory.create_async(email="shopper@example.com")
    raw = _message("shopper@example.com", html="<p>x</p>")

    missing = await _deliver(db_session, _address(owner), raw, secret=None)
    wrong = await _deliver(db_session, _address(owner), raw, secret="guess")

    assert (missing.status_code, wrong.status_code) == (401, 401)
    assert await _receipts(db_session, owner) == []


@pytest.mark.asyncio
async def test_the_same_message_delivered_twice_is_one_receipt(db_session: AsyncSession) -> None:
    owner = await UserFactory.create_async(email="shopper@example.com")
    raw = _message("shopper@example.com", html="<p>x</p>")

    await _deliver(db_session, _address(owner), raw)
    await _deliver(db_session, _address(owner), raw)

    assert len(await _receipts(db_session, owner)) == 1


@pytest.mark.asyncio
async def test_past_the_daily_limit_mail_is_dropped(db_session: AsyncSession) -> None:
    owner = await UserFactory.create_async(email="shopper@example.com")
    for n in range(2):
        raw = _message("shopper@example.com", html="<p>x</p>", msg_id=f"<r{n}@shop>")
        await _deliver(db_session, _address(owner), raw)

    third = await _deliver(
        db_session, _address(owner), _message("shopper@example.com", msg_id="<r3@shop>")
    )

    assert third.json()["reason"] == "daily_limit"
    assert len(await _receipts(db_session, owner)) == 2


@pytest.mark.asyncio
async def test_a_regenerated_address_stops_the_old_one_working(db_session: AsyncSession) -> None:
    owner = await UserFactory.create_async(email="shopper@example.com")
    old = _address(owner)
    owner.forwarding_token = "fedcba9876543210"
    await db_session.flush()

    response = await _deliver(db_session, old, _message("shopper@example.com", html="<p>x</p>"))

    assert response.json()["reason"] == "unknown_recipient"


@pytest.mark.asyncio
async def test_mail_past_the_monthly_receipt_quota_is_dropped_unread(
    db_session: AsyncSession,
) -> None:
    """F10.6: a forwarded receipt is a read like an upload, and counts the same."""
    owner = await UserFactory.create_async(email="shopper@example.com", role="user")
    parser = StubParser()

    with patch.object(get_settings(), "monthly_receipt_quota", 0):
        response = await _deliver(
            db_session,
            _address(owner),
            _message("shopper@example.com", html="<p>x</p>"),
            parser=parser,
        )

    assert response.json() == {"status": "dropped", "reason": "over_quota"}
    assert (await _receipts(db_session, owner), parser.read) == ([], [])


@pytest.mark.asyncio
async def test_a_receipt_with_no_readable_date_is_stored_on_the_day_it_arrived(
    db_session: AsyncSession,
) -> None:
    """It is never held back for a date nobody can type in (BRD A11, D3)."""
    owner = await UserFactory.create_async(email="shopper@example.com")
    undated = StubParser()
    undated.parse = _without_date(undated.parse)  # type: ignore[method-assign]

    await _deliver(
        db_session,
        _address(owner),
        _message("shopper@example.com", html="<p>x</p>"),
        parser=undated,
    )

    [receipt] = await _receipts(db_session, owner)
    assert receipt.transaction_date is not None
    assert receipt.transaction_date.date() == datetime.now(UTC).date()
    assert receipt.status == ReceiptStatus.PARSED


def _without_date(parse: Any) -> Any:
    async def parse_without_date(images: list[bytes], *, mime_types: Any = None) -> Any:
        reading = await parse(images, mime_types=mime_types)
        return reading.model_copy(update={"transaction_date": None})

    return parse_without_date
