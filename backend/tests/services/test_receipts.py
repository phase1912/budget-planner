import pytest

from app.api.errors import UnsupportedFileFormatError
from app.services.receipts import ReceiptService


def test_validate_receipt_file_accepts_valid_formats() -> None:
    service = ReceiptService()

    # Valid JPEG magic numbers
    jpeg_content = b"\xff\xd8\xff\xe0\x00\x10\x4a\x46\x49\x46\x00\x01"
    # Valid PNG magic numbers
    png_content = b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a"
    # Valid PDF magic numbers
    pdf_content = b"%PDF-1.4\n%"

    # These should not raise
    service.validate_receipt_file(jpeg_content)
    service.validate_receipt_file(png_content)
    service.validate_receipt_file(pdf_content)


def test_validate_receipt_file_rejects_invalid_formats() -> None:
    service = ReceiptService()

    # Plain text file content
    txt_content = b"This is just some plain text, not a photo."

    with pytest.raises(UnsupportedFileFormatError) as exc_info:
        service.validate_receipt_file(txt_content)

    assert "Receipts come in as JPEG, PNG, HEIC or a PDF scan" in str(exc_info.value)
