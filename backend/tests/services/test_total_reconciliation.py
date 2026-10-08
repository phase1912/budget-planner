"""Lines that miss the total go back to the model before the user is asked (BRD A9, A11)."""

import uuid
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.models.user import User
from app.ports.storage import receipt_object_name
from app.schemas.extraction import ExtractedLineItem, ExtractedReceipt
from app.services.receipt import RECHECK_ATTEMPTS, ReceiptService


def _reading(total: str, *prices: str) -> ExtractedReceipt:
    return ExtractedReceipt(
        merchant_name="Biedronka",
        transaction_date="2026-10-03",
        receipt_total=total,
        line_items=[
            ExtractedLineItem(name=f"Item {n}", quantity="1", unit_price=p, total_price=p)
            for n, p in enumerate(prices)
        ],
    )


class StubRechecker:
    """Answers each recheck with the next reading it was given."""

    def __init__(self, *answers: ExtractedReceipt) -> None:
        self.answers = list(answers)
        self.asked: list[tuple[list[bytes], ExtractedReceipt]] = []

    async def recheck(
        self, images: list[bytes], *, mime_types: list[str], reading: ExtractedReceipt
    ) -> ExtractedReceipt:
        self.asked.append((images, reading))
        return self.answers.pop(0)


def _service(rechecker: StubRechecker) -> tuple[ReceiptService, AsyncMock]:
    storage = AsyncMock()
    storage.download_file.return_value = b"\xff\xd8\xff\xe0 photo"
    return ReceiptService(storage_port=storage, rechecker_port=rechecker), storage


def _first(total: str, *prices: str) -> dict[str, Any]:
    return {**_reading(total, *prices).model_dump(), "file_ids": ["f1"]}


@pytest.mark.asyncio
async def test_a_second_look_that_finds_the_missing_line_is_kept() -> None:
    user = User(id=uuid.uuid4(), email="u@example.com")
    rechecker = StubRechecker(_reading("20.00", "10.00", "10.00"))
    service, storage = _service(rechecker)

    result = await service._reconcile_total(user, _first("20.00", "10.00"))

    assert result["total_reconciled_by"] == "rechecked"
    assert (result["items_sum_matches_total"], result["file_ids"]) == (True, ["f1"])
    storage.download_file.assert_awaited_with(receipt_object_name(user.id, "f1"))


@pytest.mark.asyncio
async def test_the_model_gets_a_second_try_told_what_the_first_got() -> None:
    user = User(id=uuid.uuid4(), email="u@example.com")
    still_off = _reading("20.00", "10.00", "5.00")
    rechecker = StubRechecker(still_off, _reading("20.00", "10.00", "10.00"))
    service, _ = _service(rechecker)

    result = await service._reconcile_total(user, _first("20.00", "10.00"))

    assert result["total_reconciled_by"] == "rechecked"
    assert [len(reading.line_items) for _, reading in rechecker.asked] == [1, 2]


@pytest.mark.asyncio
async def test_when_the_model_cannot_fix_it_the_user_is_asked_and_told_so() -> None:
    user = User(id=uuid.uuid4(), email="u@example.com")
    wrong = [_reading("20.00", "10.00", "1.00") for _ in range(RECHECK_ATTEMPTS)]
    service, _ = _service(StubRechecker(*wrong))
    first = _first("20.00", "10.00")

    result = await service._reconcile_total(user, first)

    assert result["total_reconciled_by"] == "unresolved"
    assert result["line_items"] == first["line_items"]


@pytest.mark.asyncio
async def test_a_second_look_that_rewrites_the_total_is_not_trusted() -> None:
    user = User(id=uuid.uuid4(), email="u@example.com")
    cheat = [_reading("10.00", "10.00") for _ in range(RECHECK_ATTEMPTS)]
    service, _ = _service(StubRechecker(*cheat))

    result = await service._reconcile_total(user, _first("20.00", "10.00"))

    assert (result["total_reconciled_by"], result["receipt_total"]) == ("unresolved", "20.00")


@pytest.mark.asyncio
async def test_a_known_cause_is_fixed_without_asking_the_model() -> None:
    user = User(id=uuid.uuid4(), email="u@example.com")
    rechecker = StubRechecker()
    service, _ = _service(rechecker)
    first = {
        **_reading("185.02", "185.02").model_dump(),
        "file_ids": ["f1"],
    }
    first["line_items"].append(
        {"name": "But Plastik kaucja", "quantity": "6", "unit_price": "0.50", "total_price": "3.00"}
    )
    first["items_sum_matches_total"] = False

    result = await service._reconcile_total(user, first)

    assert (result["total_reconciled_by"], result["receipt_total"]) == ("deposit", "188.02")
    assert result["items_sum_matches_total"] is True
    assert rechecker.asked == []


@pytest.mark.asyncio
async def test_a_reading_that_agrees_is_not_touched() -> None:
    service, _ = _service(StubRechecker())
    first = _first("10.00", "10.00")

    assert await service._reconcile_total(User(id=uuid.uuid4()), first) is first
