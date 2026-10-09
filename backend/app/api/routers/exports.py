import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import rate_limit
from app.api.dependencies import get_current_user, get_storage_service
from app.api.errors import DomainError, InvalidPeriodError, NotFoundError
from app.api.rate_limit import limiter
from app.db.session import get_db_session
from app.domain.periods import DateRange
from app.models.export_job import ExportJob, ExportKind, ExportStatus
from app.models.user import User
from app.ports.storage import StoragePort
from app.repository.export_job import ExportJobRepository
from app.schemas.export import ExportJobResponse, ExportRequest
from app.services.export import export_filename, run_export

router = APIRouter(prefix="/api/v1/exports", tags=["exports"])

_MEDIA_TYPES = {"csv": "text/csv; charset=utf-8", "json": "application/json"}


def _params(request: ExportRequest) -> dict[str, Any]:
    """The request's filters as stored on the job; a period is validated as everywhere (E2)."""
    if (request.start is None) != (request.end is None):
        raise InvalidPeriodError("Give both start and end, or neither")
    if request.start and request.end:
        try:
            DateRange(request.start, request.end)
        except ValueError as error:
            raise InvalidPeriodError(str(error)) from error
    elif request.kind is ExportKind.STATISTICS:
        raise InvalidPeriodError("A statistics export needs start and end")
    params: dict[str, Any] = {
        "start": request.start.isoformat() if request.start else None,
        "end": request.end.isoformat() if request.end else None,
    }
    if request.kind is ExportKind.RECEIPTS:
        params |= {"status": request.status.value if request.status else None, "q": request.q}
    else:
        params["compare"] = request.compare
    return {key: value for key, value in params.items() if value is not None}


@router.post("", response_model=ExportJobResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(rate_limit.EXPORT)
async def start_export(
    request: Request,
    export_request: ExportRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ExportJob:
    """Start exporting the caller's receipts or statistics as CSV or JSON (BRD N6).

    Answers at once with the job; the file is written in the background, so a
    long history never holds the request open. Poll the job until it is ready.
    Limited per client IP (F10.6.3).
    """
    params = _params(export_request)
    job = ExportJob(
        user_id=current_user.id,
        kind=export_request.kind,
        format=export_request.format,
        params=params,
        status=ExportStatus.PENDING,
        filename=export_filename(
            export_request.kind, export_request.format, params, datetime.now(UTC).date()
        ),
    )
    ExportJobRepository(session).add(job)
    await session.commit()
    await session.refresh(job)
    background_tasks.add_task(run_export, job.id)
    return job


async def _owned(job_id: uuid.UUID, session: AsyncSession) -> ExportJob:
    job = await ExportJobRepository(session).get(job_id)
    if job is None:
        raise NotFoundError("Export not found")
    return job


@router.get("/{job_id}", response_model=ExportJobResponse)
async def get_export(
    job_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ExportJob:
    """How the caller's export is going; another user's reads as not found (N2)."""
    return await _owned(job_id, session)


@router.get("/{job_id}/file")
async def download_export(
    job_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage: Annotated[StoragePort, Depends(get_storage_service)],
) -> Response:
    """The finished file, as an attachment under its export's name (BRD N6).

    Refused with 409 until the export is ready; another user's reads as not found.
    """
    job = await _owned(job_id, session)
    if job.status is not ExportStatus.READY or job.object_name is None:
        raise DomainError("The export is not ready yet.")
    content = await storage.download_file(job.object_name)
    return Response(
        content=content,
        media_type=_MEDIA_TYPES[job.format.value],
        headers={"Content-Disposition": f'attachment; filename="{job.filename}"'},
    )
