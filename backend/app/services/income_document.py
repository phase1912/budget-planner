"""Income read off a document, for the user to confirm (F23.11)."""

import filetype  # type: ignore[import-untyped]

from app.agent.core import AgentError
from app.ports.income_reading import IncomeReaderPort, IncomeReading

SUPPORTED = frozenset({"image/jpeg", "image/png", "image/heic", "application/pdf"})
MAX_BYTES = 10 * 1024 * 1024


class IncomeDocumentService:
    """Checks a payslip or transfer confirmation and has it read — nothing more.

    The document is never stored: it is read in memory and dropped, and only what the
    user then confirms becomes an income entry (`IncomeService.add`, channel document).
    """

    def __init__(self, reader: IncomeReaderPort) -> None:
        self.reader = reader

    async def read(self, content: bytes) -> IncomeReading:
        """What the document says came in.

        Raises UploadLimitExceededError over 10 MB, UnsupportedFileFormatError for
        anything but JPEG, PNG, HEIC or PDF, and DomainError when it cannot be read
        (`income_unreadable`) or is not about money received (`not_income`).
        """
        from app.api.errors import (
            DomainError,
            ProblemCode,
            UnsupportedFileFormatError,
            UploadLimitExceededError,
        )

        if len(content) > MAX_BYTES:
            raise UploadLimitExceededError(
                "The document is larger than 10 MB.",
                code=ProblemCode.PHOTOS_TOO_LARGE,
                params={"max_mb": 10},
            )
        kind = filetype.guess(content[:2048])
        if kind is None or kind.mime not in SUPPORTED:
            raise UnsupportedFileFormatError("Income documents come as JPEG, PNG, HEIC or PDF.")
        try:
            reading = await self.reader.read(content, kind.mime)
        except AgentError as error:
            raise DomainError(
                "The document could not be read.", code=ProblemCode.INCOME_UNREADABLE
            ) from error
        if not reading.is_income:
            raise DomainError(
                "This does not look like money received.", code=ProblemCode.NOT_INCOME
            )
        return reading
