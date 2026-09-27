"""Index receipts and line items for period queries (F7.1, BRD E1)

Every month total, receipts list and category statistic reads one user's
receipts by the date they are filed under — the printed date, else the upload
date — and then their line items. Without these, each of those scans both
tables whole.

Revision ID: e5b7c3d9a1f2
Revises: d4e8a1c2f0b3
Create Date: 2026-09-27 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e5b7c3d9a1f2"
down_revision: str | Sequence[str] | None = "d4e8a1c2f0b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the two indexes."""
    op.create_index(
        "ix_receipts_user_purchased",
        "receipts",
        ["user_id", sa.text("coalesce(transaction_date, created_at)")],
    )
    op.create_index("ix_line_items_receipt_id", "line_items", ["receipt_id"])


def downgrade() -> None:
    """Drop them again."""
    op.drop_index("ix_line_items_receipt_id", table_name="line_items")
    op.drop_index("ix_receipts_user_purchased", table_name="receipts")
