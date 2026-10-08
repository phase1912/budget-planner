"""Email intake: receipts users forward to their own address (F11.2).

Attachments the parser can read are stored like photos, under the owner's
prefix, so the receipt view shows them; a message with none is read from its
body text instead.
"""

import logging
import uuid

from app.domain.email_intake import InboundEmail
from app.models.receipt import ReceiptChannel
from app.models.user import User
from app.ports.ingestion import IngestionResult
from app.ports.parsing import ReceiptParserPort
from app.ports.storage import StoragePort, receipt_object_name

logger = logging.getLogger(__name__)


class EmailIngestionAdapter:
    """The email channel of `ReceiptIngestionPort`."""

    channel = ReceiptChannel.EMAIL

    def __init__(self, storage_port: StoragePort, parser_port: ReceiptParserPort) -> None:
        self.storage_port = storage_port
        self.parser_port = parser_port

    async def ingest(self, user: User, payload: InboundEmail) -> IngestionResult:
        """Store the message's readable attachments and read the receipt from them or the body.

        Raises whatever storage raises on upload; a message with nothing to read,
        or a parser failure, is reported as ``{"error": "extraction_failed"}``.
        """
        file_ids: list[str] = []
        contents: list[bytes] = []
        mime_types: list[str] = []
        for attachment in payload.attachments:
            file_id = str(uuid.uuid4())
            await self.storage_port.upload_file(
                receipt_object_name(user.id, file_id),
                attachment.content,
                attachment.content_type,
                {"owner_id": str(user.id)},
            )
            file_ids.append(file_id)
            contents.append(attachment.content)
            mime_types.append(attachment.content_type)
        if not contents and payload.text:
            contents, mime_types = [payload.text.encode("utf-8")], ["text/plain"]

        extraction: dict[str, object] = {"error": "extraction_failed"}
        if contents:
            try:
                parsed = await self.parser_port.parse(contents, mime_types=mime_types)
                extraction = parsed.model_dump(mode="json")
            except Exception:
                logger.exception("Reading an emailed receipt failed for user %s", user.id)
        extraction["file_ids"] = file_ids
        return IngestionResult(extraction=extraction, file_ids=file_ids)
