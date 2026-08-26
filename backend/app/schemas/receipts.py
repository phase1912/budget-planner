from pydantic import BaseModel


class UploadReceiptResponse(BaseModel):
    """Response returned upon successful receipt upload."""

    message: str
    file_ids: list[str] = []
