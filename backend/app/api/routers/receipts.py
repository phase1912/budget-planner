from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse

from app.api.dependencies import get_current_user, get_storage_service
from app.api.errors import UploadLimitExceededError
from app.models.user import User
from app.ports.storage import StoragePort
from app.schemas.receipts import UploadReceiptResponse
from app.services.receipts import ReceiptService
from app.services.storage import ObjectNotFoundError

router = APIRouter(prefix="/receipts", tags=["receipts"])


def get_receipt_service(
    storage_port: Annotated[StoragePort, Depends(get_storage_service)],
) -> ReceiptService:
    """Provide a ReceiptService instance."""
    return ReceiptService(storage_port)


@router.post("/upload", response_model=UploadReceiptResponse)
async def upload_receipt(
    files: list[UploadFile],
    current_user: Annotated[User, Depends(get_current_user)],
    receipt_service: Annotated[ReceiptService, Depends(get_receipt_service)],
) -> UploadReceiptResponse:
    """Accept up to 10 photos or scans for a single receipt (F2.2).

    Validates count (max 10) and total size (max 50MB) (BRD A4, A8).
    Validates that each uploaded file is a supported image or PDF (BRD A1, A2).
    """
    if len(files) > 10:
        raise UploadLimitExceededError("You can upload at most 10 photos per receipt.")

    total_size = 0
    file_ids: list[str] = []
    for file in files:
        if file.size is not None:
            total_size += file.size

        content = await file.read(2048)
        receipt_service.validate_receipt_file(content)
        await file.seek(0)

        full_content = await file.read()
        file_id = await receipt_service.store_receipt_image(
            current_user, full_content, file.content_type or "application/octet-stream"
        )
        file_ids.append(file_id)

    if total_size > 50 * 1024 * 1024:
        raise UploadLimitExceededError("The photos on this line add up to more than 50 MB.")

    return UploadReceiptResponse(message="Files accepted", file_ids=file_ids)


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
    current_user: Annotated[User, Depends(get_current_user)],
    receipt_service: Annotated[ReceiptService, Depends(get_receipt_service)],
) -> UploadReceiptResponse:
    """Accept multiple receipts in one request (F2.3.1).

    Each form field represents a distinct receipt. Its value must be a list of files.
    Limits (max 10 photos, max 50MB) are applied independently per receipt (BRD A5, A7, A8).
    Validates that each uploaded file is a supported image or PDF (BRD A1, A2).
    """
    form_data = await request.form()
    from starlette.datastructures import UploadFile as StarletteUploadFile

    file_ids: list[str] = []

    for field_name in set(form_data.keys()):
        raw_files = form_data.getlist(field_name)
        files: list[UploadFile] = [f for f in raw_files if isinstance(f, StarletteUploadFile)]  # type: ignore
        if not files:
            continue

        if len(files) > 10:
            raise UploadLimitExceededError("You can upload at most 10 photos per receipt.")

        total_size = 0
        for file in files:
            if file.size is not None:
                total_size += file.size

            content = await file.read(2048)
            receipt_service.validate_receipt_file(content)
            await file.seek(0)

            full_content = await file.read()
            file_id = await receipt_service.store_receipt_image(
                current_user, full_content, file.content_type or "application/octet-stream"
            )
            file_ids.append(file_id)

        if total_size > 50 * 1024 * 1024:
            raise UploadLimitExceededError("The photos on this line add up to more than 50 MB.")

    return UploadReceiptResponse(message="Batch accepted", file_ids=file_ids)


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
