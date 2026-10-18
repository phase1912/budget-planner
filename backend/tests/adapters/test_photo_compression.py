"""Photos are prepared for reading and kept smaller once read (F17.9.3)."""

import io
import os
import uuid
from typing import Any

import pytest
from PIL import Image

from app.adapters.photo_ingestion import (
    KEPT_PHOTO_SIDE,
    READ_PHOTO_SIDE,
    PhotoIngestionAdapter,
    compress_photo,
    prepare_photo,
)
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


def _jpeg(size: tuple[int, int], orientation: int | None = None) -> bytes:
    image = Image.new("RGB", size, "white")
    out = io.BytesIO()
    if orientation is None:
        image.save(out, format="JPEG")
    else:
        exif = image.getexif()
        exif[0x0112] = orientation
        image.save(out, format="JPEG", exif=exif)
    return out.getvalue()


def test_a_phone_original_is_read_at_most_3000_px_on_its_longest_side() -> None:
    content, content_type = prepare_photo(_jpeg((3024, 4032)), "image/jpeg")

    assert content_type == "image/jpeg"
    assert max(Image.open(io.BytesIO(content)).size) == READ_PHOTO_SIDE


def test_a_photo_turned_by_its_exif_tag_is_read_upright() -> None:
    content, _ = prepare_photo(_jpeg((400, 200), orientation=6), "image/jpeg")

    assert Image.open(io.BytesIO(content)).size == (200, 400)


def test_a_small_upright_jpeg_and_a_pdf_are_left_as_they_came() -> None:
    small = _jpeg((800, 1200))

    assert prepare_photo(small, "image/jpeg") == (small, "image/jpeg")
    assert prepare_photo(b"%PDF-1.7", "application/pdf") == (b"%PDF-1.7", "application/pdf")


class Keeping(Recording):
    """Storage that keeps what it is given, so a photo can be read back."""

    def __init__(self) -> None:
        super().__init__()
        self.objects: dict[str, bytes] = {}

    async def upload_file(
        self, name: str, content: bytes, content_type: str, metadata: Any = None
    ) -> str:
        self.objects[name] = content
        return await super().upload_file(name, content, content_type, metadata)

    async def download_file(self, name: str) -> bytes:
        return self.objects[name]


@pytest.mark.asyncio
async def test_a_photo_that_may_be_read_again_is_kept_whole_until_reading_is_over() -> None:
    """A recheck reads the photo as first read, never the smaller copy kept for display."""
    storage = Keeping()
    user = User(id=uuid.uuid4(), email="a@example.com")
    photo = _phone_photo(2400, 1800)
    adapter = PhotoIngestionAdapter(storage, None)  # type: ignore[arg-type]

    result = await adapter.ingest(
        user, [{"content": photo, "content_type": "image/jpeg"}], compress=False
    )
    [file_id] = result.file_ids
    name = f"receipts/{user.id}/{file_id}"
    assert storage.objects[name] == photo

    await adapter.compress_stored(user, result.file_ids)
    assert len(storage.objects[name]) < len(photo)
    assert max(Image.open(io.BytesIO(storage.objects[name])).size) <= KEPT_PHOTO_SIDE
