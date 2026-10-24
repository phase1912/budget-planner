import io
from unittest.mock import MagicMock

import pytest
from PIL import Image

from app.adapters.vision_agent import (
    LEGIBLE_SIDE,
    RECEIPT_EXTRACTION_PROMPT,
    VisionAgentAdapter,
    content_part,
    legible,
    readable_input,
)
from app.agent.core import Agent
from app.domain.receipt_conventions import COUNTRIES
from app.schemas.extraction import ExtractedLineItem, ExtractedReceipt


@pytest.mark.asyncio
async def test_vision_agent_adapter_formats_messages() -> None:
    # Given
    mock_agent = MagicMock(spec=Agent)
    mock_agent.run_structured.return_value = ExtractedReceipt(
        merchant_name="Test Store",
        currency="PLN",
        line_items=[],
    )

    adapter = VisionAgentAdapter(mock_agent)

    images = [b"fake-image-1", b"fake-image-2"]
    mime_types = ["image/jpeg", "image/png"]

    # When
    result = await adapter.parse(images, mime_types=mime_types)

    # Then
    assert result.merchant_name == "Test Store"

    # Verify the message passed to the agent
    mock_agent.run_structured.assert_called_once()
    called_messages = mock_agent.run_structured.call_args[0][0]
    assert len(called_messages) == 1

    message = called_messages[0]
    assert message.role == "user"
    assert isinstance(message.content, list)

    # Content block 0: Text prompt
    assert message.content[0]["type"] == "text"
    assert message.content[0]["text"] == RECEIPT_EXTRACTION_PROMPT

    # Content block 1: Image 1
    assert message.content[1]["type"] == "image_url"
    assert message.content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")

    # Content block 2: Image 2
    assert message.content[2]["type"] == "image_url"
    assert message.content[2]["image_url"]["url"].startswith("data:image/png;base64,")


def _photo(size: tuple[int, int], orientation: int | None = None) -> bytes:
    """A receipt-like photo: a white strip with dark print on a mid-grey table."""
    image = Image.new("RGB", size, (128, 128, 128))
    strip = (size[0] // 4, size[1] // 8, size[0] * 3 // 4, size[1] * 7 // 8)
    image.paste((250, 250, 250), strip)
    image.paste((20, 20, 20), (strip[0] + 5, strip[1] + 5, strip[0] + 30, strip[1] + 10))
    out = io.BytesIO()
    exif = Image.Exif()
    if orientation:
        exif[0x0112] = orientation
    image.save(out, format="JPEG", exif=exif)
    return out.getvalue()


def test_a_sideways_photo_is_turned_upright_and_cut_to_the_receipt() -> None:
    data, mime = legible(_photo((400, 200), orientation=6), "image/jpeg")

    prepared = Image.open(io.BytesIO(data))
    assert mime == "image/jpeg"
    assert prepared.mode == "L"
    assert prepared.height > prepared.width
    assert prepared.width < 200


def test_a_huge_photo_is_sent_no_larger_than_the_model_reads_in_full() -> None:
    data, _ = legible(_photo((5000, 9000)), "image/jpeg")

    assert max(Image.open(io.BytesIO(data)).size) <= LEGIBLE_SIDE


def test_what_is_not_a_readable_photo_goes_as_it_came() -> None:
    assert legible(b"%PDF-1.4", "application/pdf") == (b"%PDF-1.4", "application/pdf")
    assert legible(b"not an image", "image/jpeg") == (b"not an image", "image/jpeg")


def test_the_prompt_carries_every_countrys_words_and_the_menu_rule() -> None:
    for country in COUNTRIES:
        assert f"- {country.code} ({country.currency})" in RECEIPT_EXTRACTION_PROMPT
    assert "Знижка".lower() in RECEIPT_EXTRACTION_PROMPT
    assert "two prices are two items" in RECEIPT_EXTRACTION_PROMPT
    assert "mcdonald" in RECEIPT_EXTRACTION_PROMPT


@pytest.mark.asyncio
async def test_recheck_formats_previous_reading_and_gap() -> None:
    """`recheck` passes the previous reading and discrepancy gap to the model (BRD A9)."""
    mock_agent = MagicMock(spec=Agent)
    expected = ExtractedReceipt(merchant_name="Store", receipt_total="10.00", line_items=[])
    mock_agent.run_structured.return_value = expected
    adapter = VisionAgentAdapter(mock_agent)

    previous = ExtractedReceipt(
        merchant_name="Store",
        receipt_total="10,00",
        line_items=[
            ExtractedLineItem(name="Item", quantity="1", unit_price="8.00", total_price="8.00")
        ],
    )
    result = await adapter.recheck([b"img"], mime_types=["image/jpeg"], reading=previous)

    assert result == expected
    called_messages = mock_agent.run_structured.call_args[0][0]
    prompt_text = called_messages[0].content[0]["text"]
    assert (
        "The lines sum to 8.00; the amount to pay you read is 10.00; the difference is -2.00."
        in prompt_text
    )


def test_content_part_handles_plain_text_and_pdf() -> None:
    """Text and PDF attachments are formatted into text and file content blocks (F11.2)."""
    text_block = content_part(b"Receipt text", "text/plain")
    pdf_block = content_part(b"%PDF-1.4", "application/pdf")

    assert text_block == {"type": "text", "text": "Receipt text"}
    assert pdf_block["type"] == "file"


def test_readable_input_passes_non_heic_and_handles_invalid_heic() -> None:
    """Non-HEIC passes unchanged; invalid HEIC bytes fall back gracefully to original bytes."""
    assert readable_input(b"jpeg", "image/jpeg") == (b"jpeg", "image/jpeg")
    assert readable_input(b"bad-heic", "image/heic") == (b"bad-heic", "image/heic")
