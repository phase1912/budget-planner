"""Writing an export's file from what a screen showed (F7.6, BRD N6)."""

import csv
import io
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import current_user_id
from app.domain.periods import DateRange
from app.models.category import Category
from app.models.export_job import ExportFormat, ExportJob, ExportKind, ExportStatus
from app.models.receipt import ReceiptStatus
from app.models.user import User
from app.repository.receipt import ReceiptRepository
from app.services import export as export_module
from app.services.export import ExportService, _cell, export_filename, run_export
from app.services.statistics import StatisticsService, statistics_response
from tests.api.test_budget_router import _receipt
from tests.factories.category import CategoryFactory
from tests.factories.user import UserFactory


class _Storage:
    """Keeps uploaded files in memory; substitutable for the S3 adapter (StoragePort)."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    async def upload_file(
        self, object_name: str, content: bytes, content_type: str, metadata: Any = None
    ) -> str:
        self.files[object_name] = content
        return object_name

    async def download_file(self, object_name: str) -> bytes:
        return self.files[object_name]

    async def get_object_metadata(self, object_name: str) -> dict[str, str]:
        return {}

    async def generate_presigned_url(self, object_name: str, expiration_seconds: int = 3600) -> str:
        return f"memory://{object_name}"

    async def delete_file(self, object_name: str) -> None:
        self.files.pop(object_name, None)


async def _groceries(session: AsyncSession) -> Category:
    """The built-in Groceries category, created if another suite's cleanup removed the seed."""
    stmt = select(Category).where(Category.name == "Groceries", Category.user_id.is_(None))
    existing = (await session.execute(stmt)).scalar_one_or_none()
    return existing or await CategoryFactory.create_async(name="Groceries", user_id=None)


async def _shop(
    session: AsyncSession, user: User, merchant: str, when: datetime, amount: str
) -> None:
    receipt = await _receipt(session, user, when, [amount], printed_total=amount)
    receipt.merchant_name = merchant
    receipt.line_items[0].category_id = (await _groceries(session)).id
    receipt.line_items[0].name = f"{merchant} item"
    await session.flush()


async def _job(
    session: AsyncSession, user: User, kind: ExportKind, fmt: ExportFormat, **params: Any
) -> ExportJob:
    job = ExportJob(
        user_id=user.id,
        kind=kind,
        format=fmt,
        params=params,
        status=ExportStatus.RUNNING,
        filename="x",
    )
    session.add(job)
    await session.flush()
    return job


def _rows(content: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(content.decode("utf-8"))))


def test_a_cell_that_would_run_as_a_formula_is_neutralised() -> None:
    assert [_cell("=SUM(A1)"), _cell("+48 cash"), _cell("-5 off"), _cell("@x"), _cell("Milk")] == [
        "'=SUM(A1)",
        "'+48 cash",
        "'-5 off",
        "'@x",
        "Milk",
    ]


def test_the_file_is_named_for_what_it_holds_and_the_days_it_covers() -> None:
    today = date(2026, 9, 27)
    assert (
        export_filename(
            ExportKind.STATISTICS,
            ExportFormat.CSV,
            {"start": "2026-09-01", "end": "2026-09-27"},
            today,
        )
        == "statistics-2026-09-01_2026-09-27.csv"
    )
    assert (
        export_filename(ExportKind.RECEIPTS, ExportFormat.JSON, {}, today)
        == "receipts-2026-09-27.json"
    )


@pytest.mark.asyncio
async def test_a_receipts_csv_holds_the_filtered_list_one_row_per_item(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    await _shop(db_session, user, "Biedronka", datetime(2026, 9, 10, 12, 30, tzinfo=UTC), "12.50")
    await _shop(db_session, user, "Pepco", datetime(2026, 9, 20, tzinfo=UTC), "30.00")
    await _shop(db_session, user, "August shop", datetime(2026, 8, 20, tzinfo=UTC), "99.00")
    job = await _job(
        db_session,
        user,
        ExportKind.RECEIPTS,
        ExportFormat.CSV,
        start="2026-09-01",
        end="2026-09-30",
    )
    storage = _Storage()

    await ExportService(db_session, storage).write(job)

    assert job.status is ExportStatus.READY
    rows = _rows(storage.files[f"exports/{user.id}/{job.id}.csv"])
    assert [(r["merchant"], r["item"], r["item_total"], r["category"]) for r in rows] == [
        ("Pepco", "Pepco item", "30.00", "Groceries"),
        ("Biedronka", "Biedronka item", "12.50", "Groceries"),
    ]
    assert rows[1]["purchased_at"] == "2026-09-10T12:30:00+00:00"


@pytest.mark.asyncio
async def test_a_receipts_json_nests_items_and_keeps_the_filters(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    await _shop(db_session, user, "Biedronka", datetime(2026, 9, 10, tzinfo=UTC), "12.50")
    held = await _receipt(
        db_session,
        user,
        datetime(2026, 9, 11, tzinfo=UTC),
        ["5.00"],
        status=ReceiptStatus.MANUAL_REVIEW,
    )
    job = await _job(
        db_session, user, ExportKind.RECEIPTS, ExportFormat.JSON, status="manual_review"
    )
    storage = _Storage()

    await ExportService(db_session, storage).write(job)

    body = json.loads(storage.files[job.object_name or ""])
    assert body["filters"] == {"status": "manual_review"}
    assert [r["id"] for r in body["receipts"]] == [str(held.id)]
    assert body["receipts"][0]["line_items"][0]["total_price"] == "5.00"


@pytest.mark.asyncio
async def test_a_statistics_export_holds_the_same_figures_the_screen_showed(
    db_session: AsyncSession,
) -> None:
    """The demo: open the file and the figures match the screen."""
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    await _shop(db_session, user, "Biedronka", datetime(2026, 9, 10, tzinfo=UTC), "60.00")
    await _shop(db_session, user, "Biedronka", datetime(2026, 8, 10, tzinfo=UTC), "40.00")
    params = {"start": "2026-09-01", "end": "2026-09-27", "compare": True}
    storage = _Storage()

    as_json = await _job(db_session, user, ExportKind.STATISTICS, ExportFormat.JSON, **params)
    await ExportService(db_session, storage).write(as_json)
    as_csv = await _job(db_session, user, ExportKind.STATISTICS, ExportFormat.CSV, **params)
    await ExportService(db_session, storage).write(as_csv)

    screen = statistics_response(
        await StatisticsService(ReceiptRepository(db_session)).category_statistics(
            DateRange(date(2026, 9, 1), date(2026, 9, 27)), compare=True
        )
    ).model_dump(mode="json")
    assert json.loads(storage.files[as_json.object_name or ""]) == screen
    assert _rows(storage.files[as_csv.object_name or ""]) == [
        {
            "category": "Groceries",
            "total": "60.00",
            "share_percent": "100.0",
            "items": "1",
            "previous_total": "40.00",
            "change": "20.00",
            "change_percent": "50.0",
        }
    ]


def _session_factory(session: AsyncSession) -> Any:
    @asynccontextmanager
    async def opened() -> AsyncIterator[AsyncSession]:
        yield session

    return lambda: opened


@pytest.mark.asyncio
async def test_the_background_task_marks_an_export_ready_or_failed(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failure is recorded with a message to show, so the polling screen can stop."""
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    await _shop(db_session, user, "Biedronka", datetime(2026, 9, 10, tzinfo=UTC), "12.50")
    good = await _job(db_session, user, ExportKind.RECEIPTS, ExportFormat.CSV)
    storage = _Storage()

    @asynccontextmanager
    async def fake_s3(_: Any) -> AsyncIterator[_Storage]:
        yield storage

    monkeypatch.setattr(export_module, "get_session_factory", _session_factory(db_session))
    monkeypatch.setattr(export_module, "S3StorageService", fake_s3)
    await run_export(good.id)
    assert good.status is ExportStatus.READY

    bad = await _job(db_session, user, ExportKind.STATISTICS, ExportFormat.CSV)  # no period
    await run_export(bad.id)
    await db_session.refresh(bad)
    assert (bad.status, bad.error) == (
        ExportStatus.FAILED,
        "The export could not be written. Try again.",
    )
