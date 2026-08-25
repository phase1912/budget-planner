from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile

from app.api.dependencies import get_current_user
from app.models.user import User
from app.schemas.receipts import UploadReceiptResponse
from app.services.receipts import ReceiptService

router = APIRouter(prefix="/receipts", tags=["receipts"])


def get_receipt_service() -> ReceiptService:
    """Provide a ReceiptService instance."""
    return ReceiptService()


@router.post("/upload", response_model=UploadReceiptResponse)
async def upload_receipt(
    file: UploadFile,
    current_user: Annotated[User, Depends(get_current_user)],
    receipt_service: Annotated[ReceiptService, Depends(get_receipt_service)],
) -> UploadReceiptResponse:
    """Accept a receipt photo or scan (F2.1).

    Validates that the uploaded file is a supported image or PDF (BRD A1, A2).
    """
    # Read the first chunk to inspect file content without loading huge files entirely
    content = await file.read(2048)

    # Check format (raises UnsupportedFileFormatError if invalid)
    receipt_service.validate_receipt_file(content)

    # Reset file pointer for future processing (e.g. F2.4 storage)
    await file.seek(0)

    return UploadReceiptResponse(message="File accepted")
