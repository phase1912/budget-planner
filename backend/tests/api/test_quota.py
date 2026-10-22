"""AI credits, admins and per-IP limits, over HTTP (F10.6, F21.9, BRD N2)."""

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import patch

import jwt
import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_storage_service
from app.api.routers.receipts import get_receipt_service
from app.core.config import get_settings
from app.db.session import get_db_session
from app.main import create_app
from app.models.upload_job import JobStatus, UploadJob
from app.models.user import User
from app.repository.category import CategoryRepository
from tests.factories.ai_usage import AiUsageFactory
from tests.factories.upload_job import UploadJobFactory
from tests.factories.user import UserFactory

JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"x" * 64


class NoReading:
    """Accepts uploads without reading them: these tests are about counting."""

    def validate_receipt_file(self, header: bytes) -> None:
        return None

    async def process_upload_job_task(self, *args: Any) -> None:
        return None


@pytest.fixture(autouse=True)
def limits() -> Iterator[None]:
    settings = get_settings()
    with (
        patch.object(settings, "free_monthly_credits", 30),
        patch.object(settings, "credits_per_receipt", 10.0),
        patch.object(settings, "credits_per_message", 4.0),
        patch.object(settings, "daily_credit_ceiling", 50),
        patch.object(settings, "free_receipts_per_upload", 5),
        patch.object(settings, "admin_emails", ["boss@example.com"]),
    ):
        yield


async def _call(
    session: AsyncSession, user: User, method: str, path: str, **kwargs: Any
) -> Response:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield session

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_receipt_service] = NoReading
    app.dependency_overrides[get_storage_service] = lambda: None
    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        return await client.request(method, path, **kwargs)


async def _upload(session: AsyncSession, user: User, receipts: int = 1) -> Response:
    files = {f"line_{n}": ("r.jpg", JPEG, "image/jpeg") for n in range(receipts)}
    return await _call(session, user, "POST", "/receipts/upload/batch", files=files)


async def _jobs(session: AsyncSession, user: User) -> int:
    stmt = select(func.count()).where(UploadJob.user_id == user.id)
    return int(await session.scalar(stmt) or 0)


async def _spent(user: User, credits: str, **more: Any) -> None:
    await AiUsageFactory.create_async(
        user_id=user.id, credits=Decimal(credits), created_at=datetime.now(UTC), **more
    )


@pytest.mark.asyncio
async def test_what_is_left_is_told_as_receipts_and_messages_and_a_reading_counts_at_once(
    db_session: AsyncSession,
) -> None:
    """The F21.9 demo: "about 1 receipt or 4 messages left" while one is being read."""
    user = await UserFactory.create_async(email="u@example.com", role="user")
    await _spent(user, "8.4", purpose="assistant")

    before = (await _call(db_session, user, "GET", "/users/me/quota")).json()
    await _upload(db_session, user)
    after = (await _call(db_session, user, "GET", "/users/me/quota")).json()

    assert (before["limit"], before["used"], before["remaining"]) == (30, 8, 21)
    assert (before["receipts_left"], before["messages_left"]) == (2, 5)
    assert (after["used"], after["receipts_left"], after["messages_left"]) == (18, 1, 2)
    assert after["resets_on"] > datetime.now(UTC).date().isoformat()


@pytest.mark.asyncio
async def test_past_the_credits_an_upload_is_refused_before_anything_is_read(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async(email="u@example.com", role="user")
    await _spent(user, "25")

    refused = await _upload(db_session, user)

    assert (refused.status_code, refused.json()["code"]) == (429, "quota_exceeded")
    assert refused.json()["params"]["receipts_left"] == 0
    assert refused.json()["params"]["messages_left"] == 1
    assert "renew on" in refused.json()["detail"]
    assert await _jobs(db_session, user) == 0


@pytest.mark.asyncio
async def test_a_free_upload_holds_a_few_receipts_so_the_month_cannot_go_at_once(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async(email="u@example.com", role="user")
    with patch.object(get_settings(), "free_monthly_credits", 1000):
        refused = await _upload(db_session, user, receipts=6)
        accepted = await _upload(db_session, user, receipts=5)

    assert (refused.status_code, refused.json()["code"]) == (400, "too_many_receipts")
    assert refused.json()["params"]["max"] == 5
    assert accepted.status_code == 200


@pytest.mark.asyncio
async def test_another_accounts_spending_and_work_nobody_asked_for_never_count(
    db_session: AsyncSession,
) -> None:
    mine = await UserFactory.create_async(email="me@example.com", role="user")
    other = await UserFactory.create_async(email="other@example.com", role="user")
    await _spent(other, "29")
    await _spent(mine, "29", purpose="products", charged=False)

    quota = (await _call(db_session, mine, "GET", "/users/me/quota")).json()

    assert (quota["used"], quota["remaining"]) == (0, 30)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("email", "role"), [("boss@example.com", "user"), ("someone@example.com", "admin")]
)
async def test_an_admin_by_email_or_role_has_no_limit(
    db_session: AsyncSession, email: str, role: str
) -> None:
    admin = await UserFactory.create_async(email=email, role=role)
    await _spent(admin, "500")

    accepted = await _upload(db_session, admin, receipts=8)
    quota = (await _call(db_session, admin, "GET", "/users/me/quota")).json()

    assert accepted.status_code == 200
    assert (quota["unlimited"], quota["limit"], quota["receipts_left"]) == (True, None, None)


@pytest.mark.asyncio
async def test_the_whole_service_stops_at_its_daily_ceiling(
    db_session: AsyncSession,
) -> None:
    """Many accounts each within their credits still cannot run up the bill."""
    for n in range(2):
        user = await UserFactory.create_async(email=f"u{n}@example.com", role="user")
        await _spent(user, "22")
    admin = await UserFactory.create_async(email="boss@example.com", role="user")
    await _spent(admin, "400")
    late = await UserFactory.create_async(email="late@example.com", role="user")

    refused = await _upload(db_session, late)

    assert (refused.status_code, refused.json()["code"]) == (503, "service_busy")
    assert await _jobs(db_session, late) == 0


@pytest.mark.asyncio
async def test_a_receipt_is_taken_to_cost_what_receipts_lately_did(
    db_session: AsyncSession,
) -> None:
    """Once 20 were read at a price, the measured cost replaces the configured (F21.9.3)."""
    reader = await UserFactory.create_async(email="r@example.com", role="admin")
    for _ in range(20):
        await _spent(reader, "5", purpose="receipt")
        await _spent(reader, "1", purpose="categories")
    user = await UserFactory.create_async(email="u@example.com", role="user")

    quota = (await _call(db_session, user, "GET", "/users/me/quota")).json()

    assert quota["receipts_left"] == 5


@pytest.mark.asyncio
async def test_reads_with_no_recorded_price_never_make_receipts_look_free(
    db_session: AsyncSession,
) -> None:
    """Receipts read before recording began, or on a local model, cost nothing on record:
    taken as the price, "1 500 receipts left" was shown for a month of 150 credits."""
    reader = await UserFactory.create_async(email="r@example.com", role="admin")
    await UploadJobFactory.create_async(
        user_id=reader.id,
        total_items=40,
        processed_items=40,
        status=JobStatus.STORED,
        created_at=datetime.now(UTC),
    )
    for _ in range(20):
        await _spent(reader, "0", purpose="receipt", model="openai/qwen/qwen3.5-9b")
    user = await UserFactory.create_async(email="u@example.com", role="user")

    quota = (await _call(db_session, user, "GET", "/users/me/quota")).json()

    assert quota["receipts_left"] == 3


@pytest.mark.asyncio
async def test_a_receipt_added_by_hand_is_free_even_with_the_credits_spent(
    db_session: AsyncSession,
) -> None:
    """Typing a receipt in asks no model, so it never spends nor needs credits (F21.9)."""
    user = await UserFactory.create_async(email="u@example.com", role="user")
    await _spent(user, "30")
    groceries = next(
        c
        for c in await CategoryRepository(db_session).list_available(user.id)
        if c.name == "Groceries"
    )

    added = [
        await _call(
            db_session,
            user,
            "POST",
            "/receipts/manual",
            json={
                "description": f"Bread {n}",
                "spent_on": datetime.now(UTC).date().isoformat(),
                "amount": "5.00",
                "category_id": str(groceries.id),
            },
        )
        for n in range(3)
    ]
    quota = (await _call(db_session, user, "GET", "/users/me/quota")).json()

    assert [a.status_code for a in added] == [201, 201, 201]
    assert (quota["used"], quota["receipts_left"]) == (30, 0)


@pytest.mark.asyncio
async def test_registration_is_limited_per_address(db_session: AsyncSession) -> None:
    """Accounts cannot be made in bulk to get round the quota (F10.6.3)."""
    stranger = User(email="x@example.com")
    answers = [
        await _call(
            db_session,
            stranger,
            "POST",
            "/auth/register",
            json={
                "email": f"new{n}@example.com",
                "password": "Str0ng-Password!",
                "first_name": "N",
                "last_name": "N",
                "accept_terms": True,
            },
        )
        for n in range(4)
    ]

    assert [a.status_code for a in answers[:3]] == [201, 201, 201]
    assert (answers[3].status_code, answers[3].json()["code"]) == (429, "rate_limited")
    assert int(answers[3].headers["Retry-After"]) > 0
