"""shared money in a household f12 8

Revision ID: b7c1d2e3f4a5
Revises: 9d8ac0826c69
Create Date: 2026-10-19 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c1d2e3f4a5"
down_revision: str | Sequence[str] | None = "9d8ac0826c69"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("incomes", "income_sources", "regular_expenses")


def upgrade() -> None:
    """Upgrade schema: incomes and bills can be shared with a household (add-only)."""
    for table in TABLES:
        op.add_column(table, sa.Column("household_id", sa.Uuid(), nullable=True))
        op.create_index(op.f(f"ix_{table}_household_id"), table, ["household_id"], unique=False)
        op.create_foreign_key(
            f"fk_{table}_household_id_households",
            table,
            "households",
            ["household_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.add_column("regular_expenses", sa.Column("split", sa.String(length=8), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("regular_expenses", "split")
    for table in TABLES:
        op.drop_constraint(f"fk_{table}_household_id_households", table, type_="foreignkey")
        op.drop_index(op.f(f"ix_{table}_household_id"), table_name=table)
        op.drop_column(table, "household_id")
