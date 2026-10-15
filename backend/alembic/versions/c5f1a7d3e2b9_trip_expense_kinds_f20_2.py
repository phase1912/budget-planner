"""Trip expense kinds (F20.2)

Revision ID: c5f1a7d3e2b9
Revises: b4e8c2a6d9f1
Create Date: 2026-10-15 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5f1a7d3e2b9"
down_revision: str | Sequence[str] | None = "b4e8c2a6d9f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KINDS = ("transport", "accommodation", "meals", "other")


def upgrade() -> None:
    """Add-only (ADR-0014): two empty columns; a receipt read before them has no guess."""
    for column in ("expense_kind", "expense_kind_chosen"):
        op.add_column(
            "receipts",
            sa.Column(
                column,
                sa.Enum(*KINDS, name="expense_kind", native_enum=False, length=16),
                nullable=True,
            ),
        )


def downgrade() -> None:
    op.drop_column("receipts", "expense_kind_chosen")
    op.drop_column("receipts", "expense_kind")
