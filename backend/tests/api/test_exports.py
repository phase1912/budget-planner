"""Starting, following and downloading an export over HTTP (F7.6, BRD N6, N2)."""

import uuid
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_storage_service
from app.core.config import get_settings
from app.core.context import current_user_id
from app.db.session import get_db_session
from app.main import create_app
from app.models.export_job import ExportFormat, ExportJob, ExportKind, ExportStatus
from app.models.user import User
from tests.factories.user import UserFactory


class _Storage:
    async def download_file(self, object_name: str) -> bytes:
        return b"category,total\nGroceries,60.00\n"


async def _client(session: AsyncSession, user: User) -> AsyncClient:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield session

    async def override_storage() -> AsyncIterator[_Storage]:
        yield _Storage()

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_storage_service] = override_storage
    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    current_user_id.set(user.id)
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    )


async def _ready_job(session: AsyncSession, user: User) -> ExportJob:
    job = ExportJob(
        user_id=user.id,
        kind=ExportKind.STATISTICS,
        format=ExportFormat.CSV,
        params={"start": "2026-09-01", "end": "2026-09-27"},
        status=ExportStatus.READY,
        object_name=f"exports/{user.id}/x.csv",
        filename="statistics-2026-09-01_2026-09-27.csv",
    )
    session.add(job)
    await session.flush()
    return job


@pytest.mark.asyncio
async def test_an_export_is_accepted_at_once_and_written_in_the_background(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    with patch("app.api.routers.exports.run_export", new=AsyncMock()) as run:
        async with await _client(db_session, user) as client:
            response = await client.post(
                "/api/v1/exports",
                json={
                    "kind": "statistics",
                    "format": "csv",
                    "start": "2026-09-01",
                    "end": "2026-09-27",
                    "compare": True,
                },
            )

    assert response.status_code == 202, response.json()
    body = response.json()
    assert (body["status"], body["filename"]) == ("pending", "statistics-2026-09-01_2026-09-27.csv")
    run.assert_awaited_once_with(uuid.UUID(body["id"]))
    job = await db_session.get(ExportJob, uuid.UUID(body["id"]))
    assert job is not None and job.params == {
        "start": "2026-09-01",
        "end": "2026-09-27",
        "compare": True,
    }


@pytest.mark.parametrize(
    "request_body",
    [
        {"kind": "statistics", "format": "csv"},
        {"kind": "receipts", "format": "csv", "start": "2026-09-01"},
        {"kind": "receipts", "format": "json", "start": "2026-09-27", "end": "2026-09-01"},
    ],
)
@pytest.mark.asyncio
async def test_an_export_without_a_whole_period_where_one_is_needed_is_refused(
    db_session: AsyncSession, request_body: dict[str, Any]
) -> None:
    user = await UserFactory.create_async()
    async with await _client(db_session, user) as client:
        response = await client.post("/api/v1/exports", json=request_body)
    assert (response.status_code, response.json()["code"]) == (422, "invalid_period")


@pytest.mark.asyncio
async def test_a_ready_export_downloads_under_its_name(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    job = await _ready_job(db_session, user)
    async with await _client(db_session, user) as client:
        status = await client.get(f"/api/v1/exports/{job.id}")
        file = await client.get(f"/api/v1/exports/{job.id}/file")

    assert status.json()["status"] == "ready"
    assert file.status_code == 200
    assert file.headers["content-disposition"] == (
        'attachment; filename="statistics-2026-09-01_2026-09-27.csv"'
    )
    assert file.text == "category,total\nGroceries,60.00\n"


@pytest.mark.asyncio
async def test_an_export_still_being_written_cannot_be_downloaded(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    job = await _ready_job(db_session, user)
    job.status = ExportStatus.RUNNING
    await db_session.flush()
    async with await _client(db_session, user) as client:
        response = await client.get(f"/api/v1/exports/{job.id}/file")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_another_users_export_is_not_found(db_session: AsyncSession) -> None:
    """BRD N2: neither its progress nor its file is reachable, and it reads as absent."""
    owner = await UserFactory.create_async()
    job = await _ready_job(db_session, owner)
    stranger = await UserFactory.create_async()
    async with await _client(db_session, stranger) as client:
        status = await client.get(f"/api/v1/exports/{job.id}")
        file = await client.get(f"/api/v1/exports/{job.id}/file")
    assert (status.status_code, file.status_code) == (404, 404)
