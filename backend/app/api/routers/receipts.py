import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.categorisation_agent import ItemCategoriserAdapter
from app.adapters.vision_agent import VisionAgentAdapter
from app.agent.core import Agent
from app.api.dependencies import get_current_user, get_storage_service
from app.api.errors import UploadLimitExceededError
from app.core.config import get_settings
from app.db.session import get_db_session
from app.domain.categories import ItemView
from app.models.receipt import ReceiptStatus
from app.models.upload_job import JobStatus, UploadJob
from app.models.user import User
from app.ports.categorisation import ItemCategoriserPort
from app.ports.parsing import CURRENT_PARSER_VERSION
from app.ports.storage import StoragePort
from app.repository.category import CategoryRepository
from app.repository.receipt import ReceiptRepository
from app.schemas.extraction import ExtractedReceipt
from app.schemas.receipt import (
    CommitJobRequest,
    EditLineItemRequest,
    LineItemListResponse,
    LineItemResponse,
    PaginatedReceiptsResponse,
    ReceiptDetailResponse,
    ReceiptResponse,
    ResolveDuplicateRequest,
    ResolvePositionMatchRequest,
    ResolveTotalRequest,
    ReviewQueueItemResponse,
    UpdateLineItemCategoryRequest,
    UpdateReceiptRequest,
    UploadJobStatusResponse,
    UploadReceiptResponse,
)
from app.services.categorisation import CategorisationService
from app.services.receipt import ReceiptService
from app.services.storage import ObjectNotFoundError

router = APIRouter(prefix="/receipts", tags=["receipts"])


def _build_agent() -> Agent:
    """The LLM client every AI port is backed by, configured from settings."""
    settings = get_settings()
    api_key = settings.llm_api_key.get_secret_value() if settings.llm_api_key else None
    return Agent(
        model=settings.llm_model,
        api_key=api_key,
        api_base=settings.llm_api_base,
        disable_reasoning=settings.llm_disable_reasoning,
        disable_json_schema=settings.llm_disable_json_schema,
    )


def get_item_categoriser() -> ItemCategoriserPort:
    """Provide the categoriser port; tests override this to stay off the network."""
    return ItemCategoriserAdapter(_build_agent())


def get_receipt_service(
    storage_port: Annotated[StoragePort, Depends(get_storage_service)],
) -> ReceiptService:
    """Provide a ReceiptService with storage and vision parser wired up."""
    settings = get_settings()
    agent = _build_agent()
    return ReceiptService(
        storage_port,
        parser_port=VisionAgentAdapter(agent),
        categoriser_port=ItemCategoriserAdapter(agent),
        max_concurrency=settings.llm_max_concurrency,
        job_timeout_seconds=settings.upload_job_timeout_seconds,
    )


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
        job_id=job.id,
        status=job.status,
        file_ids=job.file_ids,
        extracted_data=job.result_data,
        total_items=job.total_items or 0,
        processed_items=job.processed_items or 0,
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
        job_id=job.id,
        status=job.status,
        file_ids=job.file_ids,
        extracted_data=job.result_data,
        total_items=job.total_items or 0,
        processed_items=job.processed_items or 0,
    )


@router.post("/upload/{job_id}/resolve-position-match", response_model=UploadJobStatusResponse)
async def resolve_position_match(
    job_id: uuid.UUID,
    request_data: ResolvePositionMatchRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UploadJobStatusResponse:
    """Resolve a position match conflict by overriding the decision (BRD B7)."""
    receipt_service = ReceiptService(repository=ReceiptRepository(session))
    try:
        response = await receipt_service.resolve_position_match(
            job_id, current_user.id, request_data
        )
        await session.commit()
        return response
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e)) from e
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/line-items", response_model=LineItemListResponse)
async def list_line_items(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    view: ItemView = ItemView.NEEDS_REVIEW,
    q: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> LineItemListResponse:
    """One page of the caller's line items for a categorisation view, oldest first (C3, C4)."""
    repo = ReceiptRepository(session)
    items, total = await repo.list_items(
        view,
        search=q,
        start_date=start_date,
        end_date=end_date,
        skip=(page - 1) * size,
        limit=size,
    )
    return LineItemListResponse(
        items=[ReviewQueueItemResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
        needs_review_count=await repo.count_needs_review(),
    )


@router.get("", response_model=PaginatedReceiptsResponse)
async def list_receipts(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = 1,
    size: int = 20,
    status: ReceiptStatus | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    q: str | None = None,
) -> PaginatedReceiptsResponse:
    """List an account's stored receipts newest first with pagination (F3.8)."""
    if page < 1:
        page = 1
    if size < 1:
        size = 20

    repo = ReceiptRepository(session)
    items, total = await repo.list_paginated(
        skip=(page - 1) * size,
        limit=size,
        status=status,
        start_date=start_date,
        end_date=end_date,
        search_query=q,
    )
    pages = (total + size - 1) // size if size else 0

    return PaginatedReceiptsResponse(
        items=[ReceiptResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get("/{receipt_id}", response_model=ReceiptDetailResponse)
async def get_receipt(
    receipt_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ReceiptDetailResponse:
    """Get a receipt's detail including its line items (F3.8)."""
    repo = ReceiptRepository(session)
    receipt = await repo.get_with_items(receipt_id)

    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    return ReceiptDetailResponse.model_validate(receipt)


@router.patch("/{receipt_id}", response_model=ReceiptDetailResponse)
async def update_receipt(
    receipt_id: uuid.UUID,
    request_data: UpdateReceiptRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ReceiptDetailResponse:
    """Correct a stored receipt's header and line items (F3.9, BRD A9, A11)."""
    receipt_service = ReceiptService(repository=ReceiptRepository(session))
    try:
        receipt = await receipt_service.update_receipt(receipt_id, request_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    await session.commit()
    return ReceiptDetailResponse.model_validate(receipt)


@router.delete("/{receipt_id}", status_code=204)
async def delete_receipt(
    receipt_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    storage_port: Annotated[StoragePort, Depends(get_storage_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """Permanently delete a receipt together with its line items and photos."""
    receipt_service = ReceiptService(
        storage_port=storage_port, repository=ReceiptRepository(session)
    )

    if not await receipt_service.delete_receipt(receipt_id):
        raise HTTPException(status_code=404, detail="Receipt not found")

    await session.commit()


@router.post("/upload/{job_id}/resolve-total", response_model=UploadJobStatusResponse)
async def resolve_total(
    job_id: uuid.UUID,
    request_data: ResolveTotalRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UploadJobStatusResponse:
    """Resolve a missing or low-confidence total (F4.7)."""
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

    extraction["receipt_total"] = request_data.receipt_total
    extraction["receipt_total_confidence"] = 100

    parsed = ExtractedReceipt(**extraction)

    import copy

    updated_extraction = copy.deepcopy(extraction)
    updated_extraction["computed_total"] = (
        str(parsed.computed_total) if parsed.computed_total is not None else None
    )
    updated_extraction["items_sum_matches_total"] = parsed.items_sum_matches_total
    updated_extraction["requires_manual_review"] = parsed.requires_manual_review

    extractions[idx] = updated_extraction
    job.result_data = copy.deepcopy(job.result_data)
    await session.commit()

    return UploadJobStatusResponse(
        job_id=job.id,
        status=job.status,
        file_ids=job.file_ids,
        extracted_data=job.result_data,
        total_items=job.total_items or 0,
        processed_items=job.processed_items or 0,
    )


@router.post("/upload/{job_id}/line-item", response_model=UploadJobStatusResponse)
async def edit_line_item(
    job_id: uuid.UUID,
    request_data: EditLineItemRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UploadJobStatusResponse:
    """Correct a line item the parser misread, before the batch is stored (BRD A9)."""
    receipt_service = ReceiptService(repository=ReceiptRepository(session))
    try:
        response = await receipt_service.edit_extracted_line_item(
            job_id, current_user.id, request_data
        )
        await session.commit()
        return response
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e)) from e
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/upload/{job_id}/commit", response_model=UploadJobStatusResponse)
async def commit_job(
    job_id: uuid.UUID,
    request: CommitJobRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UploadJobStatusResponse:
    """Commit all resolved extractions to the database (F4.7)."""
    stmt = select(UploadJob).where(UploadJob.id == job_id, UploadJob.user_id == current_user.id)
    job = (await session.execute(stmt)).scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.result_data or "extractions" not in job.result_data:
        raise HTTPException(status_code=400, detail="Job has no extractions")

    extractions = job.result_data["extractions"]

    selected = set(request.indices_to_store)
    if not selected:
        raise HTTPException(status_code=400, detail="No extractions selected")

    out_of_range = sorted(i for i in selected if not 0 <= i < len(extractions))
    if out_of_range:
        raise HTTPException(status_code=400, detail=f"Unknown extraction indices: {out_of_range}")

    for i, extraction in enumerate(extractions):
        if i not in selected:
            continue

        # A failed parse carries none of the fields the checks below look at, so
        # without this it passes every one of them and stores an empty receipt.
        if extraction.get("error"):
            raise HTTPException(status_code=400, detail=f"Extraction {i} failed to parse")
        if extraction.get("is_duplicate") and not extraction.get("duplicate_resolved"):
            raise HTTPException(status_code=400, detail=f"Extraction {i} has unresolved duplicate")
        if extraction.get("requires_manual_review"):
            raise HTTPException(status_code=400, detail=f"Extraction {i} requires manual review")
        if extraction.get("receipt_total_confidence", 100) < 80:
            raise HTTPException(status_code=400, detail=f"Extraction {i} has low confidence total")

        position_matches = extraction.get("position_matches") or []
        for match in position_matches:
            if match.get("result") not in ("same", "different"):
                raise HTTPException(
                    status_code=400, detail=f"Extraction {i} has unresolved position match"
                )

    repo = ReceiptRepository(session).bypass_ownership()
    for i, extraction in enumerate(extractions):
        if i not in selected:
            continue
        if extraction.get("duplicate_resolved") == "skip":
            continue

        repo.create_from_extraction(
            user_id=current_user.id,
            file_ids=extraction.get("file_ids", []),
            extraction=extraction,
            parser_version=CURRENT_PARSER_VERSION,
        )

    job.status = JobStatus.STORED
    await session.commit()

    return UploadJobStatusResponse(
        job_id=job.id,
        status=job.status,
        file_ids=job.file_ids,
        extracted_data=job.result_data,
        total_items=job.total_items or 0,
        processed_items=job.processed_items or 0,
    )


@router.patch("/line-items/{item_id}/category", response_model=LineItemResponse)
async def update_line_item_category(
    item_id: uuid.UUID,
    request_data: UpdateLineItemCategoryRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LineItemResponse:
    """Reassign one line item to a category of the owner's choosing (BRD C4)."""
    service = CategorisationService(ReceiptRepository(session), CategoryRepository(session))
    item = await service.reassign(
        item_id,
        request_data.category_id,
        current_user.id,
        apply_to_future=request_data.apply_to_future,
    )
    await session.commit()
    return LineItemResponse.model_validate(item)


@router.post("/{receipt_id}/categorise", response_model=ReceiptDetailResponse)
async def recategorise_receipt(
    receipt_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    categoriser: Annotated[ItemCategoriserPort, Depends(get_item_categoriser)],
) -> ReceiptDetailResponse:
    """Re-run automatic categorisation on a stored receipt, sparing manual choices (C3, C4)."""
    service = CategorisationService(
        ReceiptRepository(session), CategoryRepository(session), categoriser
    )
    receipt = await service.recategorise(receipt_id, current_user.id)
    await session.commit()
    return ReceiptDetailResponse.model_validate(receipt)
