"""Every JobStatus the code writes must exist in the database enum (F4.7).

``commit_job`` moves a job to STORED, which the enum type originally lacked, so
the final step of the upload wizard failed against a real database while the
mocked router tests stayed green.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.upload_job import JobStatus
from tests.factories.upload_job import UploadJobFactory
from tests.factories.user import UserFactory


@pytest.mark.parametrize("status", list(JobStatus))
async def test_every_job_status_can_be_persisted(
    db_session: AsyncSession, status: JobStatus
) -> None:
    # Given
    user = await UserFactory.create_async(email=f"status-{status.value}@example.com")

    # When
    job = await UploadJobFactory.create_async(user_id=user.id, status=status)

    # Then
    await db_session.refresh(job)
    assert job.status == status
