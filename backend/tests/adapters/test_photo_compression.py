"""Photos are kept smaller once read (F17.9.3)."""

import io
import os
import uuid
from typing import Any

import pytest
from PIL import Image

from app.adapters.photo_ingestion import KEPT_PHOTO_SIDE, PhotoIngestionAdapter, compress_photo
from app.models.user import User


def _phone_photo(width: int = 4000, height: int = 3000) -> bytes:
    """A large photo-like picture: noise does not compress, as a real shot does not."""
    image = Image.frombytes("RGB", (width, height), os.urandom(width * height * 3))
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=95)
    return out.getvalue()


def test_a_phone_photo_is_kept_as_a_jpeg_of_at_most_2000_px() -> None:
    original = _phone_photo()

    kept = compress_photo(original)

    assert kept is not None and len(kept) < len(original)
    with Image.open(io.BytesIO(kept)) as image:
        assert image.format == "JPEG"
        assert max(image.size) == KEPT_PHOTO_SIDE


def test_what_is_not_a_picture_is_kept_as_it_is() -> None:
    assert compress_photo(b"%PDF-1.7 not a picture") is None


class Recording:
    def __init__(self) -> None:
        self.uploads: list[tuple[str, int, str]] = []

    async def upload_file(
        self, name: str, content: bytes, content_type: str, metadata: Any = None
    ) -> str:
        self.uploads.append((name, len(content), content_type))
        return name


@pytest.mark.asyncio
async def test_a_stored_photo_is_replaced_by_its_kept_version_and_a_pdf_is_not() -> None:
    storage = Recording()
    user = User(id=uuid.uuid4(), email="a@example.com")
    photo = _phone_photo(2400, 1800)

    result = await PhotoIngestionAdapter(storage, None).ingest(  # type: ignore[arg-type]
        user,
        [
            {"content": photo, "content_type": "image/jpeg"},
            {"content": b"%PDF-1.7", "content_type": "application/pdf"},
        ],
    )

    first, pdf = result.file_ids
    names = [name for name, _, _ in storage.uploads]
    assert names.count(f"receipts/{user.id}/{first}") == 2
    assert names.count(f"receipts/{user.id}/{pdf}") == 1
    kept = storage.uploads[-1]
    assert kept[2] == "image/jpeg" and kept[1] < len(photo)
