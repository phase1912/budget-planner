"""Decisions taken in the upload wizard must reach the database, not just the response.

The wizard's endpoints edit `UploadJob.result_data`, a JSON column, in place.
SQLAlchemy cannot see such edits, so a missing `flag_modified` returns the
change to the browser and silently drops it: the commit then refuses the
receipt the user has just fixed. Mocked sessions cannot catch this, hence a
real database here.
"""

from collections.abc import AsyncGenerator
from typing import Any

import jwt
import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.context import current_user_id
from app.db.session import get_db_session
from app.main import create_app
from app.models.upload_job import JobStatus, UploadJob
from app.models.user import User
from tests.factories.upload_job import UploadJobFactory
from tests.factories.user import UserFactory


def _unreadable_total(**overrides: Any) -> dict[str, Any]:
    """The pepco receipt: lines read, date read, printed total not."""
    return {
        "merchant_name": "pepco",
        "transaction_date": "2026-09-14",
        "currency": "PLN",
        "receipt_total": None,
        "requires_manual_review": True,
        "computed_total": "37.00",
        "line_items": [
            {"name": "Kubek", "quantity": "1", "unit_price": "7.00", "total_price": "7.00"},
            {"name": "Patelnia", "quantity": "1", "unit_price": "30.00", "total_price": "30.00"},
        ],
        **overrides,
    }


async def _job(user: User, extraction: dict[str, Any]) -> UploadJob:
    return await UploadJobFactory.create_async(
        user_id=user.id,
        status=JobStatus.COMPLETED,
        file_ids=[],
        result_data={"extractions": [extraction]},
    )


async def _post(session: AsyncSession, user: User, url: str, json: Any) -> Response:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = override_get_db
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


async def _stored_extraction(session: AsyncSession, job: UploadJob) -> dict[str, Any]:
    """The job as the database holds it, not as this session remembers it."""
    await session.flush()
    session.expire(job)
    await session.refresh(job)
    assert job.result_data is not None
    extraction: dict[str, Any] = job.result_data["extractions"][0]
    return extraction


@pytest.mark.asyncio
async def test_a_typed_total_is_saved_and_the_receipt_can_then_be_stored(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    job = await _job(user, _unreadable_total())

    resolved = await _post(
        db_session,
        user,
        f"/receipts/upload/{job.id}/resolve-total",
        {"extraction_index": 0, "receipt_total": "37,00"},
    )
    assert resolved.status_code == 200, resolved.json()

    stored = await _stored_extraction(db_session, job)
    assert stored["receipt_total"] == "37.00"
    assert stored["requires_manual_review"] is False

    committed = await _post(
        db_session, user, f"/receipts/upload/{job.id}/commit", {"indices_to_store": [0]}
    )
    assert committed.status_code == 200, committed.json()


@pytest.mark.asyncio
@pytest.mark.parametrize(("action", "resolution"), [("store", "stored"), ("skip", "skipped")])
async def test_a_duplicate_decision_is_saved(
    db_session: AsyncSession, action: str, resolution: str
) -> None:
    user = await UserFactory.create_async()
    job = await _job(user, _unreadable_total(receipt_total="37.00", is_duplicate=True))

    response = await _post(
        db_session,
        user,
        f"/receipts/upload/{job.id}/resolve-duplicate",
        {"extraction_index": 0, "action": action},
    )
    assert response.status_code == 200, response.json()

    stored = await _stored_extraction(db_session, job)
    assert stored["is_duplicate"] is False
    assert stored["duplicate_resolved"] == resolution
