"""Products (F16.1)

Revision ID: f2a8c4d6e1b3
Revises: e5c9a1f3b7d2
Create Date: 2026-10-14 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2a8c4d6e1b3"
down_revision: str | Sequence[str] | None = "e5c9a1f3b7d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _audit() -> list[sa.Column]:  # type: ignore[type-arg]
    return [
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    """Add-only (ADR-0014): new tables and a nullable link; lines match on first use."""
    op.create_table(
        "products",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("size_amount", sa.Numeric(12, 3), nullable=True),
        sa.Column("size_unit", sa.String(length=2), nullable=True),
        *_audit(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_products_user_id", "products", ["user_id"])
    op.create_table(
        "product_aliases",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("printed_name", sa.String(length=255), nullable=False),
        *_audit(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "key", name="uq_product_alias_key"),
    )
    op.create_index("ix_product_aliases_user_id", "product_aliases", ["user_id"])
    op.create_index("ix_product_aliases_product_id", "product_aliases", ["product_id"])
    op.add_column("line_items", sa.Column("product_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_line_items_product_id",
        "line_items",
        "products",
        ["product_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_line_items_product_id", "line_items", ["product_id"])


def downgrade() -> None:
    """Remove products and the links to them."""
    op.drop_index("ix_line_items_product_id", table_name="line_items")
    op.drop_constraint("fk_line_items_product_id", "line_items", type_="foreignkey")
    op.drop_column("line_items", "product_id")
    op.drop_table("product_aliases")
    op.drop_table("products")
