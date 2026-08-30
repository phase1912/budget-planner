import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.vision_agent import VisionAgentAdapter
from app.agent.core import Agent
from app.api.dependencies import get_current_user, get_storage_service
from app.api.errors import UploadLimitExceededError
from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.upload_job import UploadJob
from app.models.user import User
from app.ports.storage import StoragePort
from app.repository.receipt import ReceiptRepository
from app.schemas.receipt import (
    ResolveDuplicateRequest,
    UploadJobStatusResponse,
    UploadReceiptResponse,
)
from app.services.receipt import ReceiptService
from app.services.storage import ObjectNotFoundError

router = APIRouter(prefix="/receipts", tags=["receipts"])


def get_receipt_service(
    storage_port: Annotated[StoragePort, Depends(get_storage_service)],
) -> ReceiptService:
    """Provide a ReceiptService with storage and vision parser wired up."""
    settings = get_settings()
    api_key = settings.llm_api_key.get_secret_value() if settings.llm_api_key else None
    agent = Agent(model=settings.llm_model, api_key=api_key)
    parser = VisionAgentAdapter(agent)
    return ReceiptService(storage_port, parser_port=parser)


@router.post("/upload", response_model=UploadReceiptResponse)
async def upload_receipt(
    files: list[UploadFile],
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    receipt_service: Annotated[ReceiptService, Depends(get_receipt_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UploadReceiptResponse:
    """Accept up to 10 photos or scans for a single receipt (F2.2).

    Validates count (max 10) and total size (max 50MB) (BRD A4, A8).
    Validates that each uploaded file is a supported image or PDF (BRD A1, A2).
    Returns immediately with a tracking handle (F2.5).
    """
    if len(files) > 10:
        raise UploadLimitExceededError("You can upload at most 10 photos per receipt.")

    total_size = 0
    files_data: list[dict[str, str | bytes]] = []

    for file in files:
        if file.size is not None:
            total_size += file.size

        content = await file.read()
        receipt_service.validate_receipt_file(content[:2048])

        files_data.append(
            {"content": content, "content_type": file.content_type or "application/octet-stream"}
        )

    if total_size > 50 * 1024 * 1024:
        raise UploadLimitExceededError("The photos on this line add up to more than 50 MB.")

    job = UploadJob(user_id=current_user.id)
    session.add(job)
    await session.commit()

    background_tasks.add_task(
        receipt_service.process_upload_job_task, job.id, current_user, [files_data]
    )

    return UploadReceiptResponse(message="Files accepted", job_id=job.id)


@router.post(
    "/upload/batch",
    response_model=UploadReceiptResponse,
    openapi_extra={
        "requestBody": {
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "array",
                            "items": {"type": "string", "format": "binary"},
                        },
                    }
                }
            }
        }
    },
)
async def upload_receipts_batch(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    receipt_service: Annotated[ReceiptService, Depends(get_receipt_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UploadReceiptResponse:
    """Accept multiple receipts in one request (F2.3.1).

    Each form field represents a distinct receipt. Its value must be a list of files.
    Limits (max 10 photos, max 50MB) are applied independently per receipt (BRD A5, A7, A8).
    Validates that each uploaded file is a supported image or PDF (BRD A1, A2).
    Returns immediately with a tracking handle (F2.5).
    """
    form_data = await request.form()
    from starlette.datastructures import UploadFile as StarletteUploadFile

    receipts_data: list[list[dict[str, str | bytes]]] = []

    field_names = sorted(
        [k for k in form_data if k.startswith("line_")],
        key=lambda x: int(x.split("_")[1]) if "_" in x and x.split("_")[1].isdigit() else 0,
    )

    for field_name in field_names:
        raw_files = form_data.getlist(field_name)
        files: list[UploadFile] = [f for f in raw_files if isinstance(f, StarletteUploadFile)]  # type: ignore
        if not files:
            continue

        if len(files) > 10:
            raise UploadLimitExceededError("You can upload at most 10 photos per receipt.")

        total_size = 0
        receipt_data: list[dict[str, str | bytes]] = []
        for file in files:
            if file.size is not None:
                total_size += file.size

            content = await file.read()
            receipt_service.validate_receipt_file(content[:2048])

            receipt_data.append(
                {
                    "content": content,
                    "content_type": file.content_type or "application/octet-stream",
                }
            )

        if total_size > 50 * 1024 * 1024:
            raise UploadLimitExceededError("The photos on this line add up to more than 50 MB.")

        receipts_data.append(receipt_data)

    job = UploadJob(user_id=current_user.id)
    session.add(job)
    await session.commit()

    background_tasks.add_task(
        receipt_service.process_upload_job_task, job.id, current_user, receipts_data
    )

    return UploadReceiptResponse(message="Batch accepted", job_id=job.id)


@router.get("/upload/{job_id}", response_model=UploadJobStatusResponse)
async def get_upload_job_status(
    job_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UploadJobStatusResponse:
    """Query the status of an asynchronous upload job (F2.5.2)."""
    stmt = select(UploadJob).where(UploadJob.id == job_id, UploadJob.user_id == current_user.id)
    job = (await session.execute(stmt)).scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return UploadJobStatusResponse(
        job_id=job.id, status=job.status, file_ids=job.file_ids, extracted_data=job.result_data
    )


@router.get("/images/{file_id}")
async def get_receipt_image(
    file_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    receipt_service: Annotated[ReceiptService, Depends(get_receipt_service)],
) -> RedirectResponse:
    """Redirects to a time-limited URL for the requested receipt image (F2.4.2)."""
    try:
        url = await receipt_service.get_presigned_url_for_image(current_user, file_id)
        return RedirectResponse(url=url)
    except ObjectNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found") from None


@router.post("/upload/{job_id}/resolve-duplicate", response_model=UploadJobStatusResponse)
async def resolve_duplicate(
    job_id: uuid.UUID,
    request_data: ResolveDuplicateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UploadJobStatusResponse:
    """Resolve a duplicate receipt detection by confirming or skipping (A14)."""
    stmt = select(UploadJob).where(UploadJob.id == job_id, UploadJob.user_id == current_user.id)
    job = (await session.execute(stmt)).scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.result_data or "extractions" not in job.result_data:
        raise HTTPException(status_code=400, detail="Job has no extractions")

    extractions = job.result_data["extractions"]
    idx = request_data.extraction_index
    if idx < 0 or idx >= len(extractions):
        raise HTTPException(status_code=400, detail="Invalid extraction index")

    extraction = extractions[idx]
    if not extraction.get("is_duplicate"):
        raise HTTPException(status_code=400, detail="Extraction is not flagged as duplicate")

    if request_data.action == "store":
        repo = ReceiptRepository(session).bypass_ownership()
        repo.create_from_extraction(
            user_id=current_user.id,
            file_ids=extraction.get("file_ids", []),
            extraction=extraction,
            parser_version="1.0.0",
        )
        extraction["is_duplicate"] = False
        extraction["duplicate_resolved"] = "stored"
    else:
        # action == "skip"
        extraction["is_duplicate"] = False
        extraction["is_skipped"] = True
        extraction["duplicate_resolved"] = "skipped"

    import copy

    job.result_data = copy.deepcopy(job.result_data)
    await session.commit()

    return UploadJobStatusResponse(
        job_id=job.id, status=job.status, file_ids=job.file_ids, extracted_data=job.result_data
    )
