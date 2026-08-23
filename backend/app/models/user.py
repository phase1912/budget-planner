"""User entity (F1.1.1)."""

from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Model


class User(Model):
    """An account in the system (BRD section 9).

    Holds identity, credentials, account-level preferences (currency, budget),
    and authorization role.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    currency: Mapped[str] = mapped_column(
        String(3), default="USD", server_default="USD", nullable=False
    )
    budget_limit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    role: Mapped[str] = mapped_column(String, default="user", server_default="user", nullable=False)
