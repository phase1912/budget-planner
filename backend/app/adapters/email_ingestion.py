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
from app.ports.income_reading import IncomeReaderPort, IncomeReading
from app.ports.ingestion import IngestionResult
from app.ports.parsing import ReceiptParserPort
from app.ports.storage import StoragePort, receipt_object_name

logger = logging.getLogger(__name__)

NOT_A_RECEIPT = 50
"""Below this `is_receipt_confidence` a forwarded document is tried as income (F23.11)."""


class EmailIngestionAdapter:
    """The email channel of `ReceiptIngestionPort`."""

    channel = ReceiptChannel.EMAIL

    def __init__(
        self,
        storage_port: StoragePort,
        parser_port: ReceiptParserPort,
        income_reader: IncomeReaderPort | None = None,
    ) -> None:
        self.storage_port = storage_port
        self.parser_port = parser_port
        self.income_reader = income_reader

    async def ingest(self, user: User, payload: InboundEmail) -> IngestionResult:
        """Store the message's readable attachments and read the receipt from them or the body.

        Raises whatever storage raises on upload; a message with nothing to read,
        or a parser failure, is reported as ``{"error": "extraction_failed"}``. A
        message that is not a receipt but a payslip or transfer confirmation comes back
        as `income`, its stored files deleted again (F23.11).
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
        maybe_income = bool(contents)
        if contents:
            try:
                parsed = await self.parser_port.parse(contents, mime_types=mime_types)
                extraction = parsed.model_dump(mode="json")
                maybe_income = (
                    parsed.document_kind == "income" or parsed.is_receipt_confidence < NOT_A_RECEIPT
                )
            except Exception:
                logger.exception("Reading an emailed receipt failed for user %s", user.id)
        if maybe_income:
            income = await self._as_income(contents[0], mime_types[0])
            if income is not None:
                for file_id in file_ids:
                    await self.storage_port.delete_file(receipt_object_name(user.id, file_id))
                return IngestionResult(extraction={}, file_ids=[], income=income)
        extraction["file_ids"] = file_ids
        return IngestionResult(extraction=extraction, file_ids=file_ids)

    async def _as_income(self, content: bytes, mime_type: str) -> IncomeReading | None:
        """The document read as money received, or None — not income, or not readable."""
        if self.income_reader is None:
            return None
        try:
            reading = await self.income_reader.read(content, mime_type)
        except Exception:
            logger.exception("Reading a forwarded document as income failed")
            return None
        return reading if reading.is_income else None
