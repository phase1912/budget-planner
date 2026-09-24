"""Add position to line_items

Line items had no order of their own, so Postgres returned them in physical
order and an updated row jumped to the end of its receipt.

Revision ID: c3a91d7e5b20
Revises: b0ffcb63fa48
Create Date: 2026-09-24 21:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c3a91d7e5b20"
down_revision: str | Sequence[str] | None = "b0ffcb63fa48"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the column and number existing items in their insertion order."""
    op.add_column(
        "line_items",
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
    )
    op.execute(
        """
        UPDATE line_items AS li
        SET position = numbered.rn - 1
        FROM (
            SELECT id, row_number() OVER (PARTITION BY receipt_id ORDER BY created_at, id) AS rn
            FROM line_items
        ) AS numbered
        WHERE li.id = numbered.id
        """
    )


def downgrade() -> None:
    """Drop the column."""
    op.drop_column("line_items", "position")
