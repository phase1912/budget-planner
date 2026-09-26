"""Drop a month's snapshot in the same flush that changes one of its receipts (BRD D6, N3).

A snapshot is a cache of derived data (domain model invariant 7). Hooking the
flush, rather than each code path that edits a receipt, is what keeps "every
mutation recalculates" true for paths not yet written: storing from the upload
wizard, editing, deleting, fixing a line. The next read rebuilds the month.

Bulk `UPDATE`/`DELETE` statements bypass the ORM and so this hook; they must
invalidate for themselves.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    ColumnElement,
    and_,
    delete,
    event,
    extract,
    func,
    inspect,
    or_,
    select,
    tuple_,
)
from sqlalchemy.orm import Session, UOWTransaction


def _moments(receipt: Any) -> list[datetime]:
    """Every date the receipt is filed under, both before and after this flush.

    A receipt moved from August to September changes two months; one not yet
    given a `created_at` by the database is being stored now.
    """
    state = inspect(receipt)
    moments: list[datetime] = []
    for attr in ("transaction_date", "created_at"):
        history = state.attrs[attr].history
        moments.extend(value for value in (*history.added, *history.deleted) if value is not None)
        current = getattr(receipt, attr, None)
        if current is not None:
            moments.append(current)
    return moments or [datetime.now(UTC)]


@event.listens_for(Session, "before_flush")
def invalidate_monthly_snapshots(session: Session, _: UOWTransaction, __: Any) -> None:
    """Delete the snapshots of every month a pending receipt or line change touches."""
    from app.models.line_item import LineItem
    from app.models.monthly_snapshot import MonthlySnapshot
    from app.models.receipt import Receipt

    months: set[tuple[uuid.UUID, int, int]] = set()
    receipt_ids: set[uuid.UUID] = set()
    for obj in (*session.new, *session.dirty, *session.deleted):
        if isinstance(obj, Receipt) and obj.user_id is not None:
            months.update((obj.user_id, m.year, m.month) for m in _moments(obj))
            if obj.id is not None:
                receipt_ids.add(obj.id)
        elif isinstance(obj, LineItem) and obj.receipt_id is not None:
            receipt_ids.add(obj.receipt_id)
    if not months and not receipt_ids:
        return

    snapshot_month = tuple_(MonthlySnapshot.user_id, MonthlySnapshot.year, MonthlySnapshot.month)
    conditions: list[ColumnElement[bool]] = []
    if receipt_ids:
        # A line's receipt may not be loaded; its month is read from the database.
        purchased = func.coalesce(Receipt.transaction_date, Receipt.created_at)
        stored = select(
            Receipt.user_id, extract("year", purchased), extract("month", purchased)
        ).where(Receipt.id.in_(receipt_ids))
        conditions.append(snapshot_month.in_(stored))
    conditions.extend(
        and_(
            MonthlySnapshot.user_id == user_id,
            MonthlySnapshot.year == year,
            MonthlySnapshot.month == month,
        )
        for user_id, year, month in months
    )
    # Core, not ORM: executing through the session here would autoflush mid-flush.
    session.connection().execute(delete(MonthlySnapshot).where(or_(*conditions)))
