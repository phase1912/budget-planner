"""A payslip or transfer forwarded by email waits as income to confirm (F23.11, N2)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from typing import Any
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.email_ingestion import EmailIngestionAdapter
from app.api.routers.webhooks import get_email_ingestion
from app.core.security import create_access_token
from app.db.session import get_db_session
from app.domain.income import IncomeKind
from app.main import create_app
from app.models.income import Income
from app.models.pending_income import PendingIncome
from app.models.user import User
from app.ports.income_reading import IncomeReading
from app.schemas.extraction import ExtractedReceipt
from tests.api.test_inbound_email import (
    SECRET,
    RecordingStorage,
    StubParser,
    _address,
    _message,
    _receipts,
    relay_settings,  # noqa: F401 — the relay's settings, as in the receipt tests
)
from tests.factories.user import UserFactory

PAYSLIP = IncomeReading(
    True, Decimal("7607.55"), date(2026, 10, 10), "ACME Sp. z o.o.", IncomeKind.SALARY
)


class NotAReceiptParser:
    """The vision model unsure the document is a receipt at all."""

    async def parse(self, images: list[bytes], *, mime_types: Any = None) -> ExtractedReceipt:
        return ExtractedReceipt(is_receipt_confidence=5, line_items=[])


class StubReader:
    def __init__(self, reading: IncomeReading = PAYSLIP) -> None:
        self.reading = reading
        self.calls = 0

    async def read(self, data: bytes, mime_type: str) -> IncomeReading:
        self.calls += 1
        return self.reading


class DeletingStorage(RecordingStorage):
    def __init__(self) -> None:
        super().__init__()
        self.deleted: list[str] = []

    async def delete_file(self, object_name: str) -> None:
        self.deleted.append(object_name)


async def _deliver(
    session: AsyncSession, to: str, raw: bytes, parser: Any, reader: StubReader, storage: Any
) -> Response:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield session

    @asynccontextmanager
    async def same_session() -> AsyncIterator[AsyncSession]:
        yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_email_ingestion] = lambda: EmailIngestionAdapter(
        storage, parser, reader
    )
    headers = {
        "X-Inbound-Recipient": to,
        "X-Inbound-Secret": SECRET,
        "Content-Type": "message/rfc822",
    }
    with patch("app.services.receipt.get_session_factory", return_value=same_session):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            return await client.post("/api/v1/webhooks/inbound-email", content=raw, headers=headers)


async def _api(
    session: AsyncSession, user: User, method: str, url: str, json: Any = None
) -> Response:
    async def same_session() -> AsyncIterator[AsyncSession]:
        yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = same_session
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {create_access_token(user.id)}"},
    ) as client:
        return await client.request(method, url, json=json)


async def _pending(session: AsyncSession, user: User) -> list[PendingIncome]:
    rows = await session.execute(select(PendingIncome).where(PendingIncome.user_id == user.id))
    return list(rows.scalars())


@pytest.mark.asyncio
async def test_a_forwarded_payslip_waits_as_income_and_its_file_is_not_kept(
    db_session: AsyncSession,
) -> None:
    owner = await UserFactory.create_async(email="worker@example.com")
    storage = DeletingStorage()
    raw = _message("worker@example.com", pdf=b"%PDF-1.4 payslip", msg_id="<pay-1@acme>")

    await _deliver(db_session, _address(owner), raw, NotAReceiptParser(), StubReader(), storage)

    [pending] = await _pending(db_session, owner)
    assert (pending.amount, pending.source, pending.kind) == (
        Decimal("7607.55"),
        "ACME Sp. z o.o.",
        "salary",
    )
    assert await _receipts(db_session, owner) == []
    assert storage.deleted == storage.uploaded and storage.uploaded


@pytest.mark.asyncio
async def test_the_same_letter_delivered_twice_waits_once(db_session: AsyncSession) -> None:
    owner = await UserFactory.create_async(email="worker@example.com")
    raw = _message("worker@example.com", pdf=b"%PDF-1.4 payslip", msg_id="<pay-2@acme>")

    for _ in range(2):
        await _deliver(
            db_session, _address(owner), raw, NotAReceiptParser(), StubReader(), DeletingStorage()
        )

    assert len(await _pending(db_session, owner)) == 1


@pytest.mark.asyncio
async def test_a_receipt_never_asks_the_income_reader(db_session: AsyncSession) -> None:
    owner = await UserFactory.create_async(email="shopper@example.com")
    reader = StubReader()

    await _deliver(
        db_session,
        _address(owner),
        _message("shopper@example.com", html="<p>Woda 2,50</p>"),
        StubParser(),
        reader,
        DeletingStorage(),
    )

    assert reader.calls == 0
    assert len(await _receipts(db_session, owner)) == 1


@pytest.mark.asyncio
async def test_neither_receipt_nor_income_still_goes_to_review_as_before(
    db_session: AsyncSession,
) -> None:
    owner = await UserFactory.create_async(email="worker@example.com")
    nothing = IncomeReading(False, None, None, None, IncomeKind.OTHER)

    await _deliver(
        db_session,
        _address(owner),
        _message("worker@example.com", pdf=b"%PDF-1.4 newsletter", msg_id="<news@x>"),
        NotAReceiptParser(),
        StubReader(nothing),
        DeletingStorage(),
    )

    assert await _pending(db_session, owner) == []
    assert len(await _receipts(db_session, owner)) == 1


@pytest.mark.asyncio
async def test_confirming_makes_it_an_entry_read_from_a_document(db_session: AsyncSession) -> None:
    owner = await UserFactory.create_async()
    pending = PendingIncome(user_id=owner.id, amount=Decimal("7607.55"), kind="salary")
    db_session.add(pending)
    await db_session.flush()

    listed = (await _api(db_session, owner, "GET", "/api/v1/income/pending")).json()
    saved = await _api(
        db_session,
        owner,
        "POST",
        f"/api/v1/income/pending/{pending.id}",
        {"received_on": "2026-10-10", "amount": "7600.00", "source": "ACME", "kind": "salary"},
    )

    assert [p["amount"] for p in listed] == ["7607.55"]
    assert saved.status_code == 201
    assert (saved.json()["channel"], saved.json()["amount"]) == ("document", "7600.00")
    assert await _pending(db_session, owner) == []
    entries = await db_session.execute(select(Income).where(Income.user_id == owner.id))
    assert len(list(entries.scalars())) == 1


@pytest.mark.asyncio
async def test_dismissing_drops_it_without_an_entry(db_session: AsyncSession) -> None:
    owner = await UserFactory.create_async()
    pending = PendingIncome(user_id=owner.id, amount=Decimal("10.00"), kind="other")
    db_session.add(pending)
    await db_session.flush()

    response = await _api(db_session, owner, "DELETE", f"/api/v1/income/pending/{pending.id}")

    assert response.status_code == 204
    assert await _pending(db_session, owner) == []


@pytest.mark.asyncio
async def test_another_users_pending_income_is_neither_seen_nor_touched(
    db_session: AsyncSession,
) -> None:
    """N2."""
    owner = await UserFactory.create_async()
    stranger = await UserFactory.create_async()
    pending = PendingIncome(user_id=owner.id, amount=Decimal("10.00"), kind="other")
    db_session.add(pending)
    await db_session.flush()

    listed = (await _api(db_session, stranger, "GET", "/api/v1/income/pending")).json()
    confirmed = await _api(
        db_session,
        stranger,
        "POST",
        f"/api/v1/income/pending/{pending.id}",
        {"received_on": "2026-10-10", "amount": "10.00", "source": "x", "kind": "other"},
    )
    dismissed = await _api(db_session, stranger, "DELETE", f"/api/v1/income/pending/{pending.id}")

    assert listed == []
    assert (confirmed.status_code, dismissed.status_code) == (404, 404)
    assert len(await _pending(db_session, owner)) == 1


class PayslipReadAsReceiptParser:
    """The model sure it can read the document, and saying it is money received."""

    async def parse(self, images: list[bytes], *, mime_types: Any = None) -> ExtractedReceipt:
        return ExtractedReceipt(is_receipt_confidence=90, document_kind="income", line_items=[])


@pytest.mark.asyncio
async def test_a_document_the_reader_calls_income_is_income_however_legible(
    db_session: AsyncSession,
) -> None:
    owner = await UserFactory.create_async(email="worker@example.com")
    raw = _message("worker@example.com", pdf=b"%PDF-1.4 payslip", msg_id="<pay-3@acme>")

    await _deliver(
        db_session,
        _address(owner),
        raw,
        PayslipReadAsReceiptParser(),
        StubReader(),
        DeletingStorage(),
    )

    assert len(await _pending(db_session, owner)) == 1
    assert await _receipts(db_session, owner) == []
