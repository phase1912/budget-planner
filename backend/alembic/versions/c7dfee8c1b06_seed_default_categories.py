"""seed_default_categories

Revision ID: c7dfee8c1b06
Revises: 52c0c9e1aa13
Create Date: 2026-09-19 18:43:22.287707

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7dfee8c1b06"
down_revision: str | Sequence[str] | None = "52c0c9e1aa13"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# We use fixed UUIDs so they are stable across environments if referenced.
DEFAULT_CATEGORIES = [
    {"id": "00000000-0000-0000-0000-000000000001", "name": "Groceries"},
    {"id": "00000000-0000-0000-0000-000000000002", "name": "Dining"},
    {"id": "00000000-0000-0000-0000-000000000003", "name": "Transport"},
    {"id": "00000000-0000-0000-0000-000000000004", "name": "Utilities"},
    {"id": "00000000-0000-0000-0000-000000000005", "name": "Health"},
    {"id": "00000000-0000-0000-0000-000000000006", "name": "Entertainment"},
    {"id": "00000000-0000-0000-0000-000000000007", "name": "Other"},
    {"id": "00000000-0000-0000-0000-000000000008", "name": "Uncategorized"},
]


def upgrade() -> None:
    """Upgrade schema."""
    categories_table = sa.table(
        "categories",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("user_id", sa.Uuid()),
    )

    op.bulk_insert(
        categories_table,
        [{"id": cat["id"], "name": cat["name"], "user_id": None} for cat in DEFAULT_CATEGORIES],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM categories WHERE user_id IS NULL")
