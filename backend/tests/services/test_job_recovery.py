"""A restart must not leave upload jobs stranded in PROCESSING (F2.2)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.upload_job import JobStatus
from app.services.job_recovery import fail_orphaned_upload_jobs
from tests.factories.upload_job import UploadJobFactory
from tests.factories.user import UserFactory


@pytest.mark.asyncio
@pytest.mark.parametrize("stranded", [JobStatus.PENDING, JobStatus.PROCESSING])
async def test_job_left_unfinished_by_a_restart_is_failed(
    db_session: AsyncSession, stranded: JobStatus
) -> None:
    # Given
    user = await UserFactory.create_async(email=f"orphan-{stranded.value}@example.com")
    job = await UploadJobFactory.create_async(user_id=user.id, status=stranded)

    # When
    orphaned = await fail_orphaned_upload_jobs(db_session)

    # Then
    assert orphaned == 1
    await db_session.refresh(job)
    assert job.status == JobStatus.FAILED


@pytest.mark.asyncio
async def test_finished_jobs_are_left_alone(db_session: AsyncSession) -> None:
    # Given
    user = await UserFactory.create_async(email="finished-owner@example.com")
    completed = await UploadJobFactory.create_async(user_id=user.id, status=JobStatus.COMPLETED)
    failed = await UploadJobFactory.create_async(user_id=user.id, status=JobStatus.FAILED)

    # When
    orphaned = await fail_orphaned_upload_jobs(db_session)

    # Then
    assert orphaned == 0
    await db_session.refresh(completed)
    await db_session.refresh(failed)
    assert completed.status == JobStatus.COMPLETED
    assert failed.status == JobStatus.FAILED
