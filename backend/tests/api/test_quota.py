"""Receipt-read quotas, admins and per-IP limits, over HTTP (F10.6, BRD N2)."""

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
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
from app.models.receipt import ReceiptChannel
from app.models.upload_job import UploadJob
from app.models.user import User
from tests.factories.receipt import ReceiptFactory
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
        patch.object(settings, "monthly_receipt_quota", 3),
        patch.object(settings, "daily_receipt_read_ceiling", 5),
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


@pytest.mark.asyncio
async def test_an_account_counts_down_its_months_receipts(db_session: AsyncSession) -> None:
    """The F10.6 demo: "2 of 3 receipts left this month"."""
    user = await UserFactory.create_async(email="u@example.com", role="user")

    await _upload(db_session, user)
    quota = (await _call(db_session, user, "GET", "/users/me/quota")).json()

    assert (quota["limit"], quota["used"], quota["remaining"], quota["unlimited"]) == (
        3,
        1,
        2,
        False,
    )
    assert quota["resets_on"] > datetime.now(UTC).date().isoformat()


@pytest.mark.asyncio
async def test_past_the_quota_an_upload_is_refused_before_anything_is_read(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async(email="u@example.com", role="user")
    await _upload(db_session, user, receipts=2)

    refused = await _upload(db_session, user, receipts=2)

    assert (refused.status_code, refused.json()["code"]) == (429, "quota_exceeded")
    assert "1 left" in refused.json()["detail"] and "resets on" in refused.json()["detail"]
    assert await _jobs(db_session, user) == 1


@pytest.mark.asyncio
async def test_emailed_receipts_count_toward_the_quota(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async(email="u@example.com", role="user")
    for _ in range(3):
        await ReceiptFactory.create_async(
            user_id=user.id, channel=ReceiptChannel.EMAIL, created_at=datetime.now(UTC)
        )

    refused = await _upload(db_session, user)

    assert refused.json()["code"] == "quota_exceeded"


@pytest.mark.asyncio
async def test_another_accounts_reads_never_count_against_mine(db_session: AsyncSession) -> None:
    mine = await UserFactory.create_async(email="me@example.com", role="user")
    other = await UserFactory.create_async(email="other@example.com", role="user")
    await _upload(db_session, other, receipts=3)

    quota = (await _call(db_session, mine, "GET", "/users/me/quota")).json()

    assert quota["used"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("email", "role"), [("boss@example.com", "user"), ("someone@example.com", "admin")]
)
async def test_an_admin_by_email_or_role_has_no_limit(
    db_session: AsyncSession, email: str, role: str
) -> None:
    admin = await UserFactory.create_async(email=email, role=role)

    for _ in range(4):
        accepted = await _upload(db_session, admin, receipts=2)
        assert accepted.status_code == 200
    quota = (await _call(db_session, admin, "GET", "/users/me/quota")).json()

    assert (quota["unlimited"], quota["limit"], quota["used"]) == (True, None, 8)


@pytest.mark.asyncio
async def test_the_whole_service_stops_reading_at_its_daily_ceiling(
    db_session: AsyncSession,
) -> None:
    """Many accounts each within their quota still cannot run up the bill."""
    for n in range(2):
        user = await UserFactory.create_async(email=f"u{n}@example.com", role="user")
        await _upload(db_session, user, receipts=2)
    admin = await UserFactory.create_async(email="boss@example.com", role="user")
    await _upload(db_session, admin, receipts=3)
    late = await UserFactory.create_async(email="late@example.com", role="user")

    refused = await _upload(db_session, late, receipts=2)

    assert (refused.status_code, refused.json()["code"]) == (503, "service_busy")
    assert (await _upload(db_session, late, receipts=1)).status_code == 200


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
            },
        )
        for n in range(4)
    ]

    assert [a.status_code for a in answers[:3]] == [201, 201, 201]
    assert (answers[3].status_code, answers[3].json()["code"]) == (429, "rate_limited")
    assert int(answers[3].headers["Retry-After"]) > 0
