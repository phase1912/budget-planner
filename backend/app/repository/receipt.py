import typing
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ColumnElement, Select, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, joinedload

from app.domain.categories import UNCATEGORIZED, ItemView
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


def _needs_review() -> ColumnElement[bool]:
    """An item the owner still has to decide on: Uncategorized, or no category at all."""
    return or_(LineItem.category_id.is_(None), Category.name == UNCATEGORIZED)


def _escape_like(term: str) -> str:
    """Make `%` and `_` in a search term match themselves rather than act as wildcards."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _purchased() -> ColumnElement[datetime]:
    """When a receipt's items were bought: its printed date, else when it was uploaded."""
    return func.coalesce(Receipt.transaction_date, Receipt.created_at)


@dataclass(frozen=True)
class ItemSpend:
    """What a set of line items cost, and what was held out of that (D1, D3)."""

    total: Decimal
    excluded_count: int
    excluded_amount: Decimal


@dataclass(frozen=True)
class CategorySpend:
    """One category's share of a set of line items; `category_id` is None for none at all."""

    category_id: uuid.UUID | None
    name: str | None
    item_count: int
    total: Decimal


class ReceiptRepository(BaseRepository[Receipt]):
    """Repository for managing receipts."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model_class=Receipt, session=session)

    def bypass_ownership(self) -> "ReceiptRepository":
        """Skip user-ownership filtering for system-level operations."""
        super().bypass_ownership()
        return self

    async def delete(self, id: uuid.UUID) -> bool:
        """Delete one of the current user's receipts through the ORM (BRD N2, D6).

        The base class deletes with a bulk statement, which the flush hook in
        `app.db.snapshot_invalidation` cannot see; deleting the loaded row lets it
        drop the month's snapshot, so the month is recalculated without it.
        Another user's receipt is not found, exactly like a missing one.
        """
        receipt = await self.get(id)
        if receipt is None:
            return False
        await self.session.delete(receipt)
        await self.session.flush()
        return True

    async def get_with_items(self, id: uuid.UUID) -> Receipt | None:
        """Fetch a receipt including its line items."""
        stmt = select(self.model_class).where(self.model_class.id == id)
        from app.models.line_item import LineItem

        stmt = stmt.options(joinedload(self.model_class.line_items).joinedload(LineItem.category))
        stmt = self._apply_ownership(stmt)
        return (await self.session.execute(stmt)).unique().scalar_one_or_none()

    def _filtered_items(
        self,
        view: ItemView,
        *,
        search: str | None,
        start_date: datetime | None,
        end_date: datetime | None,
        category_id: uuid.UUID | None,
    ) -> Select[tuple[LineItem]]:
        """The current user's line items matching the categorisation screen's filters.

        One definition of "matching", so the page, its total and its category
        breakdown can never disagree about which items they describe.
        """
        stmt = (
            select(LineItem)
            .join(Receipt, LineItem.receipt_id == Receipt.id)
            .outerjoin(Category, LineItem.category_id == Category.id)
        )
        if view is ItemView.NEEDS_REVIEW:
            stmt = stmt.where(_needs_review())
        elif view is ItemView.CORRECTED:
            stmt = stmt.where(LineItem.is_category_manual.is_(True))
        if search:
            stmt = stmt.where(LineItem.name.ilike(f"%{_escape_like(search)}%", escape="\\"))
        if start_date:
            stmt = stmt.where(_purchased() >= start_date)
        if end_date:
            stmt = stmt.where(_purchased() <= end_date)
        if category_id:
            stmt = stmt.where(LineItem.category_id == category_id)
        filtered: Select[tuple[LineItem]] = self._apply_ownership(stmt)
        return filtered

    async def list_items(
        self,
        view: ItemView,
        *,
        search: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        category_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[LineItem], int]:
        """One page of the user's line items for a categorisation view, oldest first, and the total.

        `needs_review` is the queue (BRD C3): items under Uncategorized, or left
        with no category at all. `corrected` is what the owner reassigned by hand
        (C4). "Oldest" and the date filter both use the purchase date, falling
        back to upload time for a receipt whose date was never read, so such a
        receipt is neither lost from a date range nor sorted to the end.
        """
        stmt = self._filtered_items(
            view,
            search=search,
            start_date=start_date,
            end_date=end_date,
            category_id=category_id,
        )
        total: int = (
            await self.session.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()
        page = (
            stmt.options(contains_eager(LineItem.receipt), contains_eager(LineItem.category))
            .order_by(_purchased().asc(), Receipt.id, LineItem.position)
            .offset(skip)
            .limit(limit)
        )
        return (await self.session.execute(page)).scalars().all(), total

    async def item_spend(
        self,
        view: ItemView,
        *,
        search: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        category_id: uuid.UUID | None = None,
    ) -> ItemSpend:
        """What the matching items cost, and what was held out because it is unreliable.

        Only items on `parsed` receipts count toward the total, the same rule as the
        month's budget (domain model invariant 4). Items on receipts under manual
        review are reported separately, never silently dropped (invariant 5).
        """
        matching = self._filtered_items(
            view,
            search=search,
            start_date=start_date,
            end_date=end_date,
            category_id=category_id,
        ).subquery()
        counted = Receipt.status == ReceiptStatus.PARSED
        stmt = (
            select(
                func.coalesce(func.sum(case((counted, matching.c.total_price))), 0),
                func.count().filter(~counted),
                func.coalesce(func.sum(case((~counted, matching.c.total_price))), 0),
            )
            .select_from(matching)
            .join(Receipt, Receipt.id == matching.c.receipt_id)
        )
        total, excluded_count, excluded_amount = (await self.session.execute(stmt)).one()
        return ItemSpend(Decimal(total), int(excluded_count), Decimal(excluded_amount))

    async def spend_by_category(
        self,
        view: ItemView,
        *,
        search: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[CategorySpend]:
        """The matching items' spend per category, highest first, counted like `item_spend`.

        Ignores any category filter on purpose: it is the list the user picks a
        category from, so it must keep showing the other categories.
        """
        matching = self._filtered_items(
            view, search=search, start_date=start_date, end_date=end_date, category_id=None
        ).where(Receipt.status == ReceiptStatus.PARSED)
        stmt = (
            matching.with_only_columns(
                Category.id,
                Category.name,
                func.count(LineItem.id),
                func.coalesce(func.sum(LineItem.total_price), 0),
            )
            .group_by(Category.id, Category.name)
            .order_by(func.sum(LineItem.total_price).desc(), Category.name)
        )
        return [
            CategorySpend(category_id, name, int(count), Decimal(amount))
            for category_id, name, count, amount in (await self.session.execute(stmt)).all()
        ]

    async def count_needs_review(self) -> int:
        """How many of the current user's items wait in the review queue (BRD C3)."""
        stmt = (
            select(func.count(LineItem.id))
            .join(Receipt, LineItem.receipt_id == Receipt.id)
            .outerjoin(Category, LineItem.category_id == Category.id)
            .where(_needs_review())
        )
        stmt = self._apply_ownership(stmt)
        count: int = (await self.session.execute(stmt)).scalar_one()
        return count

    async def month_total(self, start: datetime, end: datetime) -> tuple[Decimal, int]:
        """The current user's spend in `[start, end)` and how many receipts it covers (D1, D2).

        Sums line-item totals, not printed receipt totals, and only over `parsed`
        receipts: one under manual review has an unreliable total and is held
        out (domain model invariants 4 and 5). Filters on the transaction date,
        never the upload date, so a back-dated receipt lands in its own month.
        """
        in_month = select(Receipt.id).where(
            Receipt.status == ReceiptStatus.PARSED,
            Receipt.transaction_date >= start,
            Receipt.transaction_date < end,
        )
        in_month = self._apply_ownership(in_month)
        total_stmt = select(func.coalesce(func.sum(LineItem.total_price), 0)).where(
            LineItem.receipt_id.in_(in_month)
        )
        count_stmt = select(func.count()).select_from(in_month.subquery())
        total: Decimal = Decimal((await self.session.execute(total_stmt)).scalar_one())
        count: int = (await self.session.execute(count_stmt)).scalar_one()
        return total, count

    async def month_under_review(self, start: datetime, end: datetime) -> tuple[int, Decimal]:
        """How many of the user's receipts in `[start, end)` await review, and their value (D3).

        A receipt under review may lack a readable date, so it is placed by its
        purchase date where it has one and by its upload date otherwise: it must
        surface in some month, or it would be excluded without anyone being told.
        Its value is the sum of its lines, since its printed total may be the
        very thing that could not be read.
        """
        in_month = self._apply_ownership(
            select(Receipt.id).where(
                Receipt.status == ReceiptStatus.MANUAL_REVIEW,
                _purchased() >= start,
                _purchased() < end,
            )
        )
        count_stmt = select(func.count()).select_from(in_month.subquery())
        value_stmt = select(func.coalesce(func.sum(LineItem.total_price), 0)).where(
            LineItem.receipt_id.in_(in_month)
        )
        count: int = (await self.session.execute(count_stmt)).scalar_one()
        value = Decimal((await self.session.execute(value_stmt)).scalar_one())
        return count, value

    async def has_any(self) -> bool:
        """Whether the current user has stored a receipt yet; before that, `/` is a welcome."""
        stmt = self._apply_ownership(select(Receipt.id)).limit(1)
        return (await self.session.execute(stmt)).first() is not None

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

    async def get_line_item(self, item_id: uuid.UUID) -> LineItem | None:
        """Fetch one line item on a receipt the current user owns (BRD N2).

        Another user's item comes back as None, indistinguishable from one that
        does not exist.
        """
        stmt = select(LineItem).join(Receipt).where(LineItem.id == item_id)
        stmt = self._apply_ownership(stmt)
        return (await self.session.execute(stmt)).scalar_one_or_none()
