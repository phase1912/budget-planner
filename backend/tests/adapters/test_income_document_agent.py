"""Tidying the model's reading of an income document (F23.11)."""

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from app.adapters.income_document_agent import IncomeDocumentAdapter, IncomeDocumentResponse
from app.domain.income import IncomeKind


class FakeAgent:
    def __init__(self, answer: IncomeDocumentResponse) -> None:
        self.answer = answer

    async def run_structured(self, messages: Any, schema: Any, **kwargs: Any) -> Any:
        return self.answer


@pytest.mark.asyncio
async def test_amounts_and_dates_are_tidied_and_garbled_ones_dropped() -> None:
    adapter = IncomeDocumentAdapter(
        FakeAgent(  # type: ignore[arg-type]
            IncomeDocumentResponse(
                is_income=True,
                amount="6 800,50 zł",
                received_on="10.10.2026",
                source=" Acme ",
                kind=IncomeKind.SALARY,
            )
        )
    )

    reading = await adapter.read(b"\x89PNG", "image/png")

    assert reading.amount == Decimal("6800.50")
    assert reading.received_on is None
    assert reading.source == "Acme"


@pytest.mark.asyncio
async def test_a_document_that_is_not_income_carries_nothing_else() -> None:
    adapter = IncomeDocumentAdapter(
        FakeAgent(IncomeDocumentResponse(is_income=False, amount="12.00", received_on="2026-10-01"))  # type: ignore[arg-type]
    )

    reading = await adapter.read(b"\x89PNG", "image/png")

    assert reading.is_income is False
    assert reading.amount is None and reading.received_on is None


@pytest.mark.asyncio
async def test_a_valid_date_is_kept() -> None:
    adapter = IncomeDocumentAdapter(
        FakeAgent(IncomeDocumentResponse(is_income=True, amount="100", received_on="2026-10-10"))  # type: ignore[arg-type]
    )

    assert (await adapter.read(b"\x89PNG", "image/png")).received_on == date(2026, 10, 10)
