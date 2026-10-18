"""Income read off a document and confirmed by the user (F23.11, N2)."""

from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.core import AgentError
from app.api.routers.income import get_income_reader
from app.core.security import create_access_token
from app.db.session import get_db_session
from app.domain.income import IncomeKind
from app.main import create_app
from app.models.income import Income
from app.models.user import User
from app.ports.income_reading import IncomeReading
from tests.factories.user import UserFactory

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PAYSLIP = IncomeReading(
    True, Decimal("6800.00"), date(2026, 10, 10), "Acme Sp. z o.o.", IncomeKind.SALARY
)


class StubReader:
    """Stands in for the model, substitutable for `IncomeDocumentAdapter` (LSP)."""

    def __init__(self, reading: IncomeReading | None = None, fail: bool = False) -> None:
        self.reading = reading or PAYSLIP
        self.fail = fail
        self.calls = 0

    async def read(self, data: bytes, mime_type: str) -> IncomeReading:
        self.calls += 1
        if self.fail:
            raise AgentError("model down")
        return self.reading


async def _read(
    session: AsyncSession, user: User, reader: StubReader, content: bytes = PNG
) -> Response:
    async def same_session() -> AsyncIterator[AsyncSession]:
        yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = same_session
    app.dependency_overrides[get_income_reader] = lambda: reader
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {create_access_token(user.id)}"},
    ) as client:
        return await client.post(
            "/api/v1/income/read", files={"file": ("payslip.png", content, "image/png")}
        )


async def _incomes(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(Income)) or 0)


@pytest.mark.asyncio
async def test_a_payslip_comes_back_as_a_draft_and_nothing_is_saved(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async(email_confirmed_at=datetime.now(UTC))
    before = await _incomes(db_session)

    response = await _read(db_session, user, StubReader())

    assert response.status_code == 200
    assert response.json() == {
        "amount": "6800.00",
        "received_on": "2026-10-10",
        "source": "Acme Sp. z o.o.",
        "kind": "salary",
    }
    assert await _incomes(db_session) == before


@pytest.mark.asyncio
async def test_a_document_that_is_not_income_is_refused(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async(email_confirmed_at=datetime.now(UTC))
    receipt = IncomeReading(False, None, None, None, IncomeKind.OTHER)

    response = await _read(db_session, user, StubReader(receipt))

    assert response.json()["code"] == "not_income"


@pytest.mark.asyncio
async def test_a_failed_read_says_so_rather_than_inventing_an_amount(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async(email_confirmed_at=datetime.now(UTC))

    response = await _read(db_session, user, StubReader(fail=True))

    assert response.json()["code"] == "income_unreadable"


@pytest.mark.asyncio
async def test_a_file_that_is_not_a_photo_or_pdf_never_reaches_the_model(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async(email_confirmed_at=datetime.now(UTC))
    reader = StubReader()

    response = await _read(db_session, user, reader, content=b"just some text")

    assert response.status_code == 415
    assert reader.calls == 0


@pytest.mark.asyncio
async def test_a_confirmed_draft_is_kept_as_read_from_a_document_even_once_corrected(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()

    async def same_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app = create_app()
    app.dependency_overrides[get_db_session] = same_session
    entry = {"received_on": "2026-10-10", "amount": "6800.00", "source": "Acme", "kind": "salary"}
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {create_access_token(user.id)}"},
    ) as client:
        saved = await client.post("/api/v1/income", json={**entry, "channel": "document"})
        corrected = await client.put(
            f"/api/v1/income/{saved.json()['id']}", json={**entry, "amount": "6900.00"}
        )

    assert saved.json()["channel"] == "document"
    assert corrected.json()["channel"] == "document"
    assert corrected.json()["amount"] == "6900.00"
