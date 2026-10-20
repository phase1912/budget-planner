"""accounts f23 15

Revision ID: 12b7f85c9506
Revises: c4d5e6f7a8b9
Create Date: 2026-10-19 18:49:08.533818

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "12b7f85c9506"
down_revision: str | Sequence[str] | None = "c4d5e6f7a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: accounts, the money moved between them and their rules (add-only)."""

    op.create_table(
        "accounts",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("household_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("opening", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("opening_on", sa.Date(), nullable=False),
        sa.Column("tax_rate", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("for_purchases", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name=op.f("fk_accounts_household_id_households"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_accounts_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_accounts")),
    )
    op.create_index(op.f("ix_accounts_household_id"), "accounts", ["household_id"], unique=False)
    op.create_index(op.f("ix_accounts_user_id"), "accounts", ["user_id"], unique=False)
    op.create_table(
        "regular_transfers",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("day", sa.SmallInteger(), nullable=True),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("from_account_id", sa.Uuid(), nullable=False),
        sa.Column("to_account_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["from_account_id"],
            ["accounts.id"],
            name=op.f("fk_regular_transfers_from_account_id_accounts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["to_account_id"],
            ["accounts.id"],
            name=op.f("fk_regular_transfers_to_account_id_accounts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_regular_transfers_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_regular_transfers")),
    )
    op.create_index(
        op.f("ix_regular_transfers_from_account_id"),
        "regular_transfers",
        ["from_account_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_regular_transfers_to_account_id"),
        "regular_transfers",
        ["to_account_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_regular_transfers_user_id"), "regular_transfers", ["user_id"], unique=False
    )
    op.create_table(
        "account_moves",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("moved_on", sa.Date(), nullable=False),
        sa.Column("from_account_id", sa.Uuid(), nullable=True),
        sa.Column("to_account_id", sa.Uuid(), nullable=True),
        sa.Column("bill_id", sa.Uuid(), nullable=True),
        sa.Column("rule_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["bill_id"],
            ["regular_expenses.id"],
            name=op.f("fk_account_moves_bill_id_regular_expenses"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["from_account_id"],
            ["accounts.id"],
            name=op.f("fk_account_moves_from_account_id_accounts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["rule_id"],
            ["regular_transfers.id"],
            name=op.f("fk_account_moves_rule_id_regular_transfers"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["to_account_id"],
            ["accounts.id"],
            name=op.f("fk_account_moves_to_account_id_accounts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_account_moves_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_account_moves")),
    )
    op.create_index(op.f("ix_account_moves_bill_id"), "account_moves", ["bill_id"], unique=False)
    op.create_index(
        op.f("ix_account_moves_from_account_id"), "account_moves", ["from_account_id"], unique=False
    )
    op.create_index(op.f("ix_account_moves_moved_on"), "account_moves", ["moved_on"], unique=False)
    op.create_index(op.f("ix_account_moves_rule_id"), "account_moves", ["rule_id"], unique=False)
    op.create_index(
        op.f("ix_account_moves_to_account_id"), "account_moves", ["to_account_id"], unique=False
    )
    op.create_index(op.f("ix_account_moves_user_id"), "account_moves", ["user_id"], unique=False)
    op.add_column("income_sources", sa.Column("account_id", sa.Uuid(), nullable=True))
    op.add_column(
        "income_sources", sa.Column("about", sa.Boolean(), server_default="false", nullable=False)
    )
    op.create_index(
        op.f("ix_income_sources_account_id"), "income_sources", ["account_id"], unique=False
    )
    op.create_foreign_key(
        op.f("fk_income_sources_account_id_accounts"),
        "income_sources",
        "accounts",
        ["account_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("incomes", sa.Column("account_id", sa.Uuid(), nullable=True))
    op.add_column("incomes", sa.Column("source_id", sa.Uuid(), nullable=True))
    op.add_column("incomes", sa.Column("tax", sa.Numeric(precision=12, scale=2), nullable=True))
    op.create_index(op.f("ix_incomes_account_id"), "incomes", ["account_id"], unique=False)
    op.create_index(op.f("ix_incomes_source_id"), "incomes", ["source_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_incomes_source_id_income_sources"),
        "incomes",
        "income_sources",
        ["source_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        op.f("fk_incomes_account_id_accounts"),
        "incomes",
        "accounts",
        ["account_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("regular_expenses", sa.Column("account_id", sa.Uuid(), nullable=True))
    op.create_index(
        op.f("ix_regular_expenses_account_id"), "regular_expenses", ["account_id"], unique=False
    )
    op.create_foreign_key(
        op.f("fk_regular_expenses_account_id_accounts"),
        "regular_expenses",
        "accounts",
        ["account_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("tax_payments", sa.Column("account_id", sa.Uuid(), nullable=True))
    op.create_index(
        op.f("ix_tax_payments_account_id"), "tax_payments", ["account_id"], unique=False
    )
    op.create_foreign_key(
        op.f("fk_tax_payments_account_id_accounts"),
        "tax_payments",
        "accounts",
        ["account_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_constraint(
        op.f("fk_tax_payments_account_id_accounts"), "tax_payments", type_="foreignkey"
    )
    op.drop_index(op.f("ix_tax_payments_account_id"), table_name="tax_payments")
    op.drop_column("tax_payments", "account_id")
    op.drop_constraint(
        op.f("fk_regular_expenses_account_id_accounts"), "regular_expenses", type_="foreignkey"
    )
    op.drop_index(op.f("ix_regular_expenses_account_id"), table_name="regular_expenses")
    op.drop_column("regular_expenses", "account_id")
    op.drop_constraint(op.f("fk_incomes_account_id_accounts"), "incomes", type_="foreignkey")
    op.drop_constraint(op.f("fk_incomes_source_id_income_sources"), "incomes", type_="foreignkey")
    op.drop_index(op.f("ix_incomes_source_id"), table_name="incomes")
    op.drop_index(op.f("ix_incomes_account_id"), table_name="incomes")
    op.drop_column("incomes", "tax")
    op.drop_column("incomes", "source_id")
    op.drop_column("incomes", "account_id")
    op.drop_constraint(
        op.f("fk_income_sources_account_id_accounts"), "income_sources", type_="foreignkey"
    )
    op.drop_index(op.f("ix_income_sources_account_id"), table_name="income_sources")
    op.drop_column("income_sources", "about")
    op.drop_column("income_sources", "account_id")
    op.drop_index(op.f("ix_account_moves_user_id"), table_name="account_moves")
    op.drop_index(op.f("ix_account_moves_to_account_id"), table_name="account_moves")
    op.drop_index(op.f("ix_account_moves_rule_id"), table_name="account_moves")
    op.drop_index(op.f("ix_account_moves_moved_on"), table_name="account_moves")
    op.drop_index(op.f("ix_account_moves_from_account_id"), table_name="account_moves")
    op.drop_index(op.f("ix_account_moves_bill_id"), table_name="account_moves")
    op.drop_table("account_moves")
    op.drop_index(op.f("ix_regular_transfers_user_id"), table_name="regular_transfers")
    op.drop_index(op.f("ix_regular_transfers_to_account_id"), table_name="regular_transfers")
    op.drop_index(op.f("ix_regular_transfers_from_account_id"), table_name="regular_transfers")
    op.drop_table("regular_transfers")
    op.drop_index(op.f("ix_accounts_user_id"), table_name="accounts")
    op.drop_index(op.f("ix_accounts_household_id"), table_name="accounts")
    op.drop_table("accounts")
