"""Recovery for upload jobs orphaned by a process restart (F2.2).

An upload job is advanced by an in-process background task, so a deploy, a
crash or an autoreload kills it mid-flight and leaves the row in PROCESSING
with nothing left to move it on.  The client polls such a job forever, so the
application sweeps them at startup instead of letting them accumulate.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from sqlalchemy import CursorResult, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.upload_job import JobStatus, UploadJob

logger = logging.getLogger(__name__)


async def fail_orphaned_upload_jobs(session: AsyncSession) -> int:
    """Mark every unfinished job as failed, returning how many there were.

    Both PENDING and PROCESSING are swept: a process that dies before its
    background task starts strands the job just as thoroughly as one that dies
    halfway through it.

    Only safe at startup, while no background task of this process can own such
    a row yet.  It assumes a single application process: against a multi-replica
    deployment it would fail jobs another replica is still working on, so that
    setup needs job ownership rather than this sweep.
    """
    result = cast(
        "CursorResult[Any]",
        await session.execute(
            update(UploadJob)
            .where(UploadJob.status.in_([JobStatus.PENDING, JobStatus.PROCESSING]))
            .values(status=JobStatus.FAILED)
        ),
    )
    await session.commit()
    orphaned = int(result.rowcount)

    if orphaned:
        logger.warning("Failed %d upload job(s) orphaned by a restart", orphaned)
    return orphaned
