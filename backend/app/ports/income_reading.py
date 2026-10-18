"""Port for reading income from a document (F23.11)."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from app.domain.income import IncomeKind


@dataclass(frozen=True)
class IncomeReading:
    """What a payslip or transfer confirmation says came in.

    `is_income` is False when the document is not about money received — a receipt, a
    bill — and then the other fields are empty. Any field the document does not show is
    None, for the user to fill in on the confirmation card.
    """

    is_income: bool
    amount: Decimal | None
    received_on: date | None
    source: str | None
    kind: IncomeKind


class IncomeReaderPort(Protocol):
    """Read the money received from a document; separate from receipt parsing (ISP)."""

    async def read(self, data: bytes, mime_type: str) -> IncomeReading:
        """Read one document. Raises ``AgentError`` when the model call fails entirely."""
        ...
