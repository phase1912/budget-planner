import typing
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, joinedload

from app.domain.categories import UNCATEGORIZED
from app.models.category import Category
from app.models.line_item import LineItem
from app.models.match_override import PositionMatchOverride
from app.models.receipt import Receipt, ReceiptStatus
from app.models.upload_job import UploadJob
from app.repository.base import BaseRepository


def _read_category(item_data: dict[str, typing.Any]) -> tuple[uuid.UUID | None, int | None]:
    """Read one extracted item's category, refusing anything unusable.

    The id travels as a string through `UploadJob.result_data`, so a malformed
    one has to be rejected here rather than at the column. Confidence stays
    `None` when the item was never categorised — a default of 100 would file an
    unclassified item as a certainty and hide it from BRD C3's review queue.
    """
    raw_id = item_data.get("category_id")
    try:
        category_id = uuid.UUID(str(raw_id)) if raw_id else None
    except ValueError:
        category_id = None

    confidence = item_data.get("category_confidence")
    return category_id, confidence if isinstance(confidence, int) else None


class ReceiptRepository(BaseRepository[Receipt]):
    """Repository for managing receipts."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model_class=Receipt, session=session)

    def bypass_ownership(self) -> "ReceiptRepository":
        """Skip user-ownership filtering for system-level operations."""
        super().bypass_ownership()
        return self

    async def get_with_items(self, id: uuid.UUID) -> Receipt | None:
        """Fetch a receipt including its line items."""
        stmt = select(self.model_class).where(self.model_class.id == id)
        from app.models.line_item import LineItem

        stmt = stmt.options(joinedload(self.model_class.line_items).joinedload(LineItem.category))
        stmt = self._apply_ownership(stmt)
        return (await self.session.execute(stmt)).unique().scalar_one_or_none()

    async def list_uncategorized_items(self) -> typing.Sequence[LineItem]:
        """Fetch the user's line items filed under Uncategorized, oldest first (BRD C3).

        This is the categorisation review queue. "Oldest" is the purchase date,
        falling back to upload time for receipts whose date was never read, so an
        undated receipt still takes its place rather than sinking to the end.
        Receipt and item order break ties so the queue does not reshuffle.
        """
        stmt = (
            select(LineItem)
            .join(Receipt, LineItem.receipt_id == Receipt.id)
            .join(Category, LineItem.category_id == Category.id)
            .where(Category.name == UNCATEGORIZED)
            .options(contains_eager(LineItem.receipt), contains_eager(LineItem.category))
            .order_by(
                func.coalesce(Receipt.transaction_date, Receipt.created_at).asc(),
                Receipt.id,
                LineItem.id,
            )
        )
        stmt = self._apply_ownership(stmt)
        return (await self.session.execute(stmt)).scalars().all()

    async def list_paginated(
        self,
        skip: int,
        limit: int,
        status: ReceiptStatus | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        search_query: str | None = None,
    ) -> tuple[typing.Sequence[Receipt], int]:
        """Return a page of receipts and the total count, with optional filters."""
        from sqlalchemy import func, or_

        base_stmt = select(self.model_class)
        base_stmt = self._apply_ownership(base_stmt)

        if status:
            base_stmt = base_stmt.where(self.model_class.status == status)
        if start_date:
            base_stmt = base_stmt.where(self.model_class.transaction_date >= start_date)
        if end_date:
            base_stmt = base_stmt.where(self.model_class.transaction_date <= end_date)
        if search_query:
            search_term = f"%{search_query}%"
            # Receipt has merchant_name, LineItem has name
            # We use an EXISTS subquery to avoid multiplying rows before counting
            has_line_item = self.model_class.line_items.any(LineItem.name.ilike(search_term))
            base_stmt = base_stmt.where(
                or_(self.model_class.merchant_name.ilike(search_term), has_line_item)
            )

        # Count query
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = await self.session.scalar(count_stmt) or 0

        # Items query
        stmt = base_stmt.order_by(
            self.model_class.transaction_date.desc().nulls_last(),
            self.model_class.created_at.desc(),
        )
        stmt = stmt.offset(skip).limit(limit)

        stmt = stmt.options(joinedload(self.model_class.line_items))

        result = await self.session.execute(stmt)
        items = result.unique().scalars().all()
        return items, total

    async def exists_for_user(self, user_id: uuid.UUID) -> bool:
        """Check if any receipts exist for the given user."""
        from sqlalchemy import text
        from sqlalchemy.exc import ProgrammingError

        try:
            async with self.session.begin_nested():
                stmt = text("SELECT 1 FROM receipts WHERE user_id = :user_id LIMIT 1")
                result = await self.session.execute(stmt, {"user_id": user_id})
                return result.scalar() is not None
        except ProgrammingError:
            return False

    async def has_duplicate(
        self,
        user_id: uuid.UUID,
        merchant_name: str | None,
        transaction_date_str: str | None,
        total_amount_str: str | None,
    ) -> bool:
        """Check if a receipt with the same merchant, date, and total exists for the user."""
        if not merchant_name or not transaction_date_str or not total_amount_str:
            return False

        import contextlib
        from decimal import Decimal

        from sqlalchemy import Date, cast

        total_amount = None
        with contextlib.suppress(Exception):
            total_amount = Decimal(str(total_amount_str).replace(",", "."))

        if total_amount is None:
            return False

        stmt = select(self.model_class).where(
            self.model_class.user_id == user_id,
            self.model_class.merchant_name == merchant_name,
            self.model_class.total_amount == total_amount,
        )

        try:
            import datetime

            dt = datetime.datetime.strptime(transaction_date_str, "%Y-%m-%d").date()
            stmt = stmt.where(cast(self.model_class.transaction_date, Date) == dt)
        except ValueError:
            return False

        result = await self.session.execute(stmt.limit(1))
        return result.scalar_one_or_none() is not None

    def create_from_extraction(
        self,
        user_id: uuid.UUID,
        file_ids: list[str],
        extraction: dict[str, typing.Any],
        parser_version: str,
    ) -> Receipt:
        """Instantiate and save a Receipt and its LineItems from a parser extraction."""
        import contextlib
        import datetime
        from decimal import Decimal, InvalidOperation

        from app.models.line_item import LineItem
        from app.models.receipt import Receipt, ReceiptStatus

        receipt_status = (
            ReceiptStatus.MANUAL_REVIEW
            if (
                extraction.get("requires_manual_review")
                or extraction.get("items_sum_matches_total") is not True
            )
            else ReceiptStatus.PARSED
        )

        dt = None
        t_date = extraction.get("transaction_date")
        if t_date:
            try:
                d = datetime.datetime.strptime(t_date, "%Y-%m-%d")
                t_time = extraction.get("transaction_time")
                if t_time:
                    t = datetime.datetime.strptime(t_time, "%H:%M").time()
                    d = datetime.datetime.combine(d.date(), t)
                dt = d.replace(tzinfo=datetime.UTC)
            except ValueError:
                pass

        total_amt = None
        rt = extraction.get("receipt_total")
        if rt:
            with contextlib.suppress(Exception):
                total_amt = Decimal(str(rt).replace(",", "."))

        receipt = Receipt(
            user_id=user_id,
            merchant_name=extraction.get("merchant_name"),
            transaction_date=dt,
            total_amount=total_amt,
            status=receipt_status,
            file_ids=file_ids,
            parser_version=parser_version,
        )

        items_data = extraction.get("line_items", [])
        if not isinstance(items_data, list):
            items_data = []

        duplicate_indices = set()
        matches = extraction.get("position_matches", [])
        if isinstance(matches, list):
            for match in matches:
                if isinstance(match, dict) and match.get("result") == "same":
                    idx = match.get("item_b_index")
                    if isinstance(idx, int):
                        duplicate_indices.add(idx)

        line_items = []
        for i, item_data in enumerate(items_data):
            if i in duplicate_indices:
                continue
            if not isinstance(item_data, dict):
                continue
            try:
                tp_str = str(item_data.get("total_price") or "0")
                if not tp_str or tp_str == "":
                    tp_str = "0"
                tp = Decimal(tp_str.replace(",", "."))

                qty_str = str(item_data.get("quantity") or "1")
                qty = Decimal(qty_str.replace(",", "."))

                up_str = str(item_data.get("unit_price") or tp_str)
                up = Decimal(up_str.replace(",", "."))

                category_id, category_confidence = _read_category(item_data)

                line_items.append(
                    LineItem(
                        name=item_data.get("name", "Unknown Item"),
                        quantity=qty,
                        unit_price=up,
                        total_price=tp,
                        category_id=category_id,
                        category_confidence=category_confidence,
                    )
                )
            except (InvalidOperation, TypeError, ValueError):
                # The LLM failed to parse these numbers.
                # Since the receipt will be saved as MANUAL_REVIEW, the user can fix them later.
                category_id, category_confidence = _read_category(item_data)

                line_items.append(
                    LineItem(
                        name=item_data.get("name", "Unknown Item"),
                        quantity=Decimal("1"),
                        unit_price=Decimal("0"),
                        total_price=Decimal("0"),
                        category_id=category_id,
                        category_confidence=category_confidence,
                    )
                )

        receipt.line_items = line_items
        self.add(receipt)
        return receipt

    async def get_upload_job(self, job_id: uuid.UUID, user_id: uuid.UUID) -> UploadJob | None:
        stmt = select(UploadJob).where(UploadJob.id == job_id, UploadJob.user_id == user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def discard_upload_job_payloads(self, user_id: uuid.UUID, file_ids: list[str]) -> int:
        """Forget the extraction payload of every job that named these photos.

        An upload job keeps the parsed result and the file ids it produced so the
        wizard can show "What we read". Once the receipt those photos belong to
        is deleted the images are gone, and the screen would render tiles that
        load forever. Returns how many jobs were cleared.

        Only the owner's jobs are considered, so this can never reach across
        users (BRD N2).
        """
        if not file_ids:
            return 0

        # Filtered in Python rather than with a JSON containment operator:
        # UploadJob.file_ids is plain JSON, not JSONB, so an overlap test would
        # need a cast, and one user's jobs are few enough that it earns nothing.
        wanted = set(file_ids)
        stmt = select(UploadJob).where(UploadJob.user_id == user_id)
        jobs = (await self.session.execute(stmt)).scalars().all()

        cleared = 0
        for job in jobs:
            if not wanted.intersection(job.file_ids or []):
                continue
            job.file_ids = []
            job.result_data = None
            cleared += 1

        if cleared:
            await self.session.flush()

        return cleared

    async def add_position_match_override(self, override: PositionMatchOverride) -> None:
        self.session.add(override)
        # Flush is handled by unit of work / commit outside
