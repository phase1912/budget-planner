"""Exporting the user's receipts and statistics as CSV or JSON (BRD N6 — F7.6).

An export is written in the background: the request only records an `ExportJob`,
and `run_export` builds the file once the response has gone, so a long history
never holds a request open. The file holds what the screen it was asked from
showed — the receipts list under its filters, or the statistics for its period.
"""

import csv
import io
import json
import logging
import uuid
from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.context import current_user_id
from app.db.session import get_session_factory
from app.domain.periods import DateRange
from app.models.export_job import ExportFormat, ExportJob, ExportKind, ExportStatus
from app.models.receipt import Receipt, ReceiptStatus
from app.ports.storage import StoragePort
from app.repository.receipt import ReceiptRepository
from app.schemas.receipt import ReceiptResponse
from app.services.statistics import StatisticsService, statistics_response
from app.services.storage import S3StorageService

logger = logging.getLogger(__name__)

PAGE = 500
"""How many receipts are read from the database at a time while writing a file."""

_CONTENT_TYPES = {ExportFormat.CSV: "text/csv", ExportFormat.JSON: "application/json"}
_FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")


def export_filename(
    kind: ExportKind, fmt: ExportFormat, params: dict[str, Any], today: date
) -> str:
    """The name the file is saved under: what it is, the days it covers, and its format."""
    start, end = params.get("start"), params.get("end")
    days = f"{start}_{end}" if start and end else today.isoformat()
    return f"{kind.value}-{days}.{fmt.value}"


def object_name(job: ExportJob) -> str:
    """Where the file is stored: under its owner's prefix, so no key names another's (N2)."""
    return f"exports/{job.user_id}/{job.id}.{job.format.value}"


def _period(params: dict[str, Any]) -> DateRange | None:
    start, end = params.get("start"), params.get("end")
    if start is None or end is None:
        return None
    return DateRange(date.fromisoformat(start), date.fromisoformat(end))


def _cell(text: str | None) -> str:
    """A text cell safe to open in a spreadsheet: a leading =, +, - or @ is not a formula."""
    if not text:
        return ""
    return f"'{text}" if text.startswith(_FORMULA_STARTS) else text


def _csv(header: list[str], rows: Iterable[list[Any]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def receipts_csv(receipts: Sequence[Receipt]) -> bytes:
    """One row per line item, its receipt's details repeated; a receipt with none keeps one row."""
    header = [
        "receipt_id",
        "merchant",
        "purchased_at",
        "status",
        "receipt_total",
        "item",
        "quantity",
        "unit_price",
        "item_total",
        "category",
    ]
    rows: list[list[Any]] = []
    for receipt in receipts:
        head = [
            str(receipt.id),
            _cell(receipt.merchant_name),
            receipt.transaction_date.isoformat() if receipt.transaction_date else "",
            receipt.status.value,
            "" if receipt.total_amount is None else str(receipt.total_amount),
        ]
        if not receipt.line_items:
            rows.append([*head, "", "", "", "", ""])
        for item in receipt.line_items:
            category = item.category.name if item.category else None
            rows.append(
                [
                    *head,
                    _cell(item.name),
                    str(item.quantity),
                    str(item.unit_price),
                    str(item.total_price),
                    _cell(category),
                ]
            )
    return _csv(header, rows)


def receipts_json(receipts: Sequence[Receipt], params: dict[str, Any]) -> bytes:
    """The receipts as the list API returns them, line items nested, with the filters used."""
    body = {
        "exported_at": datetime.now(UTC).isoformat(),
        "filters": params,
        "receipts": [ReceiptResponse.model_validate(r).model_dump(mode="json") for r in receipts],
    }
    return json.dumps(body, ensure_ascii=False, indent=2).encode("utf-8")


class ExportService:
    """Writes one export's file and records the outcome on its job (BRD N6)."""

    def __init__(self, session: AsyncSession, storage: StoragePort) -> None:
        self.session = session
        self.storage = storage
        self.receipts = ReceiptRepository(session)

    async def write(self, job: ExportJob) -> None:
        """Build the file the job asks for, store it, and mark the job ready.

        Reads only the job owner's data: the caller sets `current_user_id` to
        `job.user_id` first, which every repository query filters by (N2).
        """
        content = await self._content(job)
        name = object_name(job)
        await self.storage.upload_file(name, content, _CONTENT_TYPES[job.format])
        job.object_name = name
        job.status = ExportStatus.READY
        job.completed_at = datetime.now(UTC)

    async def _content(self, job: ExportJob) -> bytes:
        if job.kind is ExportKind.STATISTICS:
            return await self._statistics(job)
        receipts = await self._all_receipts(job.params)
        if job.format is ExportFormat.CSV:
            return receipts_csv(receipts)
        return receipts_json(receipts, job.params)

    async def _all_receipts(self, params: dict[str, Any]) -> list[Receipt]:
        """Every receipt the list would show under these filters, newest first, page by page."""
        status = ReceiptStatus(params["status"]) if params.get("status") else None
        found: list[Receipt] = []
        while True:
            page, total = await self.receipts.list_paginated(
                len(found),
                PAGE,
                status=status,
                period=_period(params),
                search_query=params.get("q"),
            )
            found.extend(page)
            if not page or len(found) >= total:
                return found

    async def _statistics(self, job: ExportJob) -> bytes:
        period = _period(job.params)
        if period is None:
            raise ValueError("A statistics export needs a period")
        compare = bool(job.params.get("compare"))
        stats = await StatisticsService(self.receipts).category_statistics(period, compare=compare)
        response = statistics_response(stats)
        if job.format is ExportFormat.JSON:
            return response.model_dump_json(indent=2).encode("utf-8")
        header = ["category", "total", "share_percent", "items"]
        if compare:
            header += ["previous_total", "change", "change_percent"]
        rows = [
            [
                _cell(c.name or "No category"),
                str(c.total),
                str(c.share),
                c.item_count,
                *(
                    [
                        str(c.previous_total),
                        str(c.change),
                        "" if c.change_percent is None else str(c.change_percent),
                    ]
                    if compare
                    else []
                ),
            ]
            for c in response.categories
        ]
        return _csv(header, rows)


async def run_export(job_id: uuid.UUID) -> None:
    """Background task: write one export, marking its job ready or failed (BRD N6).

    Runs after the response has been sent, with its own session and storage
    client, since the request's are closed by then. A failure is recorded on the
    job, with a message fit to show, so the screen polling it can stop and say so.
    """
    async with get_session_factory()() as session:
        job = (await session.execute(select(ExportJob).where(ExportJob.id == job_id))).scalar_one()
        current_user_id.set(job.user_id)
        job.status = ExportStatus.RUNNING
        await session.commit()
        try:
            async with S3StorageService(get_settings()) as storage:
                await ExportService(session, storage).write(job)
        except Exception:
            logger.exception("Export %s failed", job_id)
            await session.rollback()
            job.status = ExportStatus.FAILED
            job.error = "The export could not be written. Try again."
            job.completed_at = datetime.now(UTC)
        await session.commit()
