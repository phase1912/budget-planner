from unittest.mock import MagicMock

import pytest

from app.adapters.vision_agent import RECEIPT_EXTRACTION_PROMPT, VisionAgentAdapter
from app.agent.core import Agent
from app.schemas.extraction import ExtractedReceipt


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
