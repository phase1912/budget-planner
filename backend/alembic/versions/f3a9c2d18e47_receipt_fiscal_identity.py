"""Fiscal identity and possible-duplicate mark on receipts (F11.3, F11.5)

Revision ID: f3a9c2d18e47
Revises: e2c4a1f07b3d
Create Date: 2026-10-09 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3a9c2d18e47"
down_revision: str | Sequence[str] | None = "e2c4a1f07b3d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add-only, so the code already running is unaffected (ADR-0014)."""
    op.add_column("receipts", sa.Column("fiscal_register_id", sa.String(length=40), nullable=True))
    op.add_column(
        "receipts", sa.Column("fiscal_receipt_number", sa.String(length=40), nullable=True)
    )
    op.add_column("receipts", sa.Column("possible_duplicate_of_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_receipts_possible_duplicate_of_id_receipts"),
        "receipts",
        "receipts",
        ["possible_duplicate_of_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_receipts_user_fiscal",
        "receipts",
        ["user_id", "fiscal_register_id", "fiscal_receipt_number"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_receipts_user_fiscal", table_name="receipts")
    op.drop_constraint(
        op.f("fk_receipts_possible_duplicate_of_id_receipts"), "receipts", type_="foreignkey"
    )
    op.drop_column("receipts", "possible_duplicate_of_id")
    op.drop_column("receipts", "fiscal_receipt_number")
    op.drop_column("receipts", "fiscal_register_id")
