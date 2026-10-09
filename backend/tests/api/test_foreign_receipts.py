"""Receipts in a foreign currency are stored in the account's (F11.7, ADR-0016, BRD D1).

The rate source is a stub at the port, so nothing here reaches the network.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import patch

import jwt
import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.email_ingestion import EmailIngestionAdapter
from app.api.dependencies import get_current_user, get_exchange_rates
from app.api.routers.webhooks import get_email_ingestion
from app.core.config import get_settings
from app.core.context import current_user_id
from app.db.session import get_db_session
from app.domain.currency import ExchangeRate
from app.main import create_app
from app.models.exchange_rate import CachedExchangeRate
from app.models.receipt import Receipt, ReceiptStatus
from app.models.user import User
from app.ports.exchange_rates import ExchangeRateUnavailable
from app.repository.exchange_rate import CachedExchangeRates
from app.schemas.extraction import ExtractedLineItem, ExtractedReceipt
from app.services.receipt import ReceiptService
from tests.api.test_inbound_email import (  # noqa: F401 — relay_settings is a fixture
    RecordingStorage,
    StubParser,
    _address,
    _message,
    relay_settings,
)
from tests.api.test_upload_wizard_persistence import _job
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory

RATE = ExchangeRate("UAH", "PLN", Decimal("0.0864"), date(2026, 10, 2), "NBP")


class StubRates:
    """Answers one rate, or none at all; counts the times it was asked."""

    def __init__(self, answer: ExchangeRate | None = RATE) -> None:
        self.answer = answer
        self.asked: list[tuple[str, str, date]] = []

    async def rate(self, base: str, quote: str, on: date) -> ExchangeRate:
        self.asked.append((base, quote, on))
        if self.answer is None:
            raise ExchangeRateUnavailable("stub has none")
        return ExchangeRate(base, quote, self.answer.rate, self.answer.effective_date, "NBP")


def _hryvnia_reading(**overrides: Any) -> dict[str, Any]:
    return {
        "merchant_name": "Silpo",
        "currency": "UAH",
        "transaction_date": "2026-10-03",
        "receipt_total": "1197.00",
        "items_sum_matches_total": True,
        "requires_manual_review": False,
        "line_items": [
            {"name": "Kava", "quantity": "1", "unit_price": "397.00", "total_price": "397.00"},
            {"name": "Syr", "quantity": "1", "unit_price": "800.00", "total_price": "800.00"},
        ],
        **overrides,
    }


async def _only_receipt(session: AsyncSession, user: User) -> Receipt:
    rows = await session.execute(select(Receipt).where(Receipt.user_id == user.id))
    [receipt] = rows.scalars().all()
    await session.refresh(receipt, ["line_items"])
    return receipt


# --- the cache --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_each_rate_is_fetched_once_and_then_read_from_the_database(
    db_session: AsyncSession,
) -> None:
    source = StubRates()
    rates = CachedExchangeRates(source, db_session)

    first = await rates.rate("UAH", "PLN", date(2026, 10, 3))
    second = await CachedExchangeRates(source, db_session).rate("UAH", "PLN", date(2026, 10, 3))

    assert first == second
    assert len(source.asked) == 1
    stored = await db_session.scalar(select(func.count()).select_from(CachedExchangeRate))
    assert stored == 1


# --- the wizard -------------------------------------------------------------------


async def _post(
    session: AsyncSession, user: User, url: str, json: Any, rates: StubRates
) -> Response:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield session

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_exchange_rates] = lambda: rates
    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    current_user_id.set(user.id)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        return await client.post(url, json=json)


@pytest.mark.asyncio
async def test_the_wizard_is_shown_the_rate_before_storing(db_session: AsyncSession) -> None:
    reading = _hryvnia_reading()

    await ReceiptService(exchange_rates=StubRates()).preview_conversion(db_session, reading, "PLN")

    assert reading["conversion"]["converted_total"] == "103.42"
    assert reading["conversion"]["rate_date"] == "2026-10-02"
    assert reading["receipt_total"] == "1197.00"


@pytest.mark.asyncio
async def test_the_wizard_says_when_there_is_no_rate(db_session: AsyncSession) -> None:
    reading = _hryvnia_reading()

    await ReceiptService(exchange_rates=StubRates(None)).preview_conversion(
        db_session, reading, "PLN"
    )

    assert reading["conversion"] == {
        "currency": "UAH",
        "account_currency": "PLN",
        "unavailable": True,
    }


@pytest.mark.asyncio
async def test_a_receipt_in_the_accounts_currency_is_not_converted(
    db_session: AsyncSession,
) -> None:
    rates = StubRates()
    reading = _hryvnia_reading(currency="PLN")

    await ReceiptService(exchange_rates=rates).preview_conversion(db_session, reading, "PLN")

    assert ("conversion" not in reading, rates.asked) == (True, [])


@pytest.mark.asyncio
async def test_a_stored_hryvnia_receipt_counts_in_zloty_and_keeps_its_hryvnias(
    db_session: AsyncSession,
) -> None:
    """The F11.7 demo: 1197 UAH is counted as 103.42 PLN, not as 1197 PLN."""
    user = await UserFactory.create_async(currency="PLN")
    job = await _job(user, _hryvnia_reading(conversion={"converted_total": "103.42"}))
    rates = StubRates()

    response = await _post(
        db_session, user, f"/receipts/upload/{job.id}/commit", {"indices_to_store": [0]}, rates
    )

    assert response.status_code == 200, response.json()
    receipt = await _only_receipt(db_session, user)
    assert receipt.total_amount == Decimal("103.42")
    assert sum(i.total_price for i in receipt.line_items) == Decimal("103.42")
    assert receipt.status == ReceiptStatus.PARSED
    assert (receipt.original_currency, receipt.original_total) == ("UAH", Decimal("1197.00"))
    assert (receipt.exchange_rate, receipt.exchange_rate_date, receipt.exchange_rate_source) == (
        Decimal("0.0864"),
        date(2026, 10, 2),
        "NBP",
    )
    assert rates.asked == [("UAH", "PLN", date(2026, 10, 3))]


@pytest.mark.asyncio
async def test_a_receipt_with_no_rate_is_held_in_review_in_its_own_amounts(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async(currency="PLN")
    job = await _job(user, _hryvnia_reading())

    await _post(
        db_session,
        user,
        f"/receipts/upload/{job.id}/commit",
        {"indices_to_store": [0]},
        StubRates(None),
    )

    receipt = await _only_receipt(db_session, user)
    assert receipt.status == ReceiptStatus.MANUAL_REVIEW
    assert receipt.total_amount == Decimal("1197.00")
    assert (receipt.original_currency, receipt.exchange_rate) == ("UAH", None)


# --- email ------------------------------------------------------------------------


class HryvniaParser(StubParser):
    async def parse(
        self, images: list[bytes], *, mime_types: list[str] | None = None
    ) -> ExtractedReceipt:
        self.read.append((images, mime_types))
        return ExtractedReceipt(
            merchant_name="Rozetka",
            currency="UAH",
            transaction_date="2026-10-03",
            receipt_total="100.00",
            items_sum_matches_total=True,
            line_items=[
                ExtractedLineItem(
                    name="Kabel", quantity="1", unit_price="100.00", total_price="100.00"
                )
            ],
        )


@pytest.mark.asyncio
@pytest.mark.usefixtures("relay_settings")
async def test_an_emailed_foreign_receipt_is_converted_too(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async(email="shopper@example.com", currency="PLN")

    @asynccontextmanager
    async def same_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_exchange_rates] = StubRates
    app.dependency_overrides[get_email_ingestion] = lambda: EmailIngestionAdapter(
        RecordingStorage(),  # type: ignore[arg-type]
        HryvniaParser(),
    )
    headers = {
        "X-Inbound-Recipient": _address(user),
        "X-Inbound-Secret": "relay-secret",
        "Content-Type": "message/rfc822",
    }
    with patch("app.services.receipt.get_session_factory", return_value=same_session):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            raw = _message(user.email, html="<p>receipt</p>")
            await c.post("/api/v1/webhooks/inbound-email", content=raw, headers=headers)

    receipt = await _only_receipt(db_session, user)
    assert (receipt.total_amount, receipt.original_total) == (Decimal("8.64"), Decimal("100.00"))
    assert receipt.original_currency == "UAH"


# --- correcting a receipt no rate was found for -----------------------------------


@pytest.mark.asyncio
async def test_amounts_typed_in_by_hand_record_the_rate_they_imply(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async(currency="PLN")
    receipt = await ReceiptFactory.create_async(
        user_id=user.id,
        merchant_name="Silpo",
        transaction_date=datetime(2026, 10, 3, tzinfo=UTC),
        total_amount=Decimal("1197.00"),
        status=ReceiptStatus.MANUAL_REVIEW,
        file_ids=[],
        original_currency="UAH",
        original_total=Decimal("1197.00"),
    )
    current_user_id.set(user.id)

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = override_get_db
    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        response = await client.patch(
            f"/receipts/{receipt.id}",
            json={
                "merchant_name": "Silpo",
                "transaction_date": "2026-10-03",
                "total_amount": "103.42",
                "line_items": [
                    {
                        "name": "Vse",
                        "quantity": "1",
                        "unit_price": "103.42",
                        "total_price": "103.42",
                    }
                ],
            },
        )

    assert response.status_code == 200, response.json()
    body = response.json()
    assert (body["status"], body["exchange_rate_source"]) == ("parsed", "manual")
    assert Decimal(body["exchange_rate"]) == Decimal("0.08639933")
