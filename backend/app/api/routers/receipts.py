from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile

from app.api.dependencies import get_current_user
from app.api.errors import UploadLimitExceededError
from app.models.user import User
from app.schemas.receipts import UploadReceiptResponse
from app.services.receipts import ReceiptService

router = APIRouter(prefix="/receipts", tags=["receipts"])


def get_receipt_service() -> ReceiptService:
    """Provide a ReceiptService instance."""
    return ReceiptService()


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
    for file in files:
        if file.size is not None:
            total_size += file.size

        content = await file.read(2048)
        receipt_service.validate_receipt_file(content)
        await file.seek(0)

    if total_size > 50 * 1024 * 1024:
        raise UploadLimitExceededError("The photos on this line add up to more than 50 MB.")

    return UploadReceiptResponse(message="Files accepted")
