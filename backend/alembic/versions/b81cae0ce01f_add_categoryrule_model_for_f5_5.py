"""Add category_rules for learning from corrections (F5.5, BRD C5)

Revision ID: b81cae0ce01f
Revises: c3a91d7e5b20
Create Date: 2026-09-24 20:31:08.172694

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b81cae0ce01f"
down_revision: str | Sequence[str] | None = "c3a91d7e5b20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the rules table, one rule per user, merchant and item name."""
    op.create_table(
        "category_rules",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("merchant_name", sa.String(length=255), nullable=False),
        sa.Column("item_name", sa.String(length=255), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_category_rules_category_id_categories"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_category_rules_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_category_rules")),
        sa.UniqueConstraint("user_id", "merchant_name", "item_name", name="uq_category_rule_item"),
    )
    op.create_index(op.f("ix_category_rules_user_id"), "category_rules", ["user_id"], unique=False)


def downgrade() -> None:
    """Drop the rules table."""
    op.drop_index(op.f("ix_category_rules_user_id"), table_name="category_rules")
    op.drop_table("category_rules")
