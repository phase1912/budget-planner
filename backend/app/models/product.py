import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Model


class Product(Model):
    """One thing the user buys, however each shop prints it (F16.1).

    Per user: another user's products are never seen or matched against (N2). `name` is
    how it is shown — the first printed name it was found under — and the size, in grams
    or millilitres, is what prices are later compared per unit by (F16.2).
    """

    __tablename__ = "products"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    size_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    size_unit: Mapped[str | None] = mapped_column(String(2), nullable=True)

    aliases: Mapped[list["ProductAlias"]] = relationship(
        "ProductAlias", back_populates="product", cascade="all, delete-orphan"
    )


class ProductAlias(Model):
    """One way a product is printed, as a matching key, with an example of it (F16.1).

    A line whose key is an alias belongs to its product, so merging or splitting moves
    aliases and the choice holds for every later receipt.
    """

    __tablename__ = "product_aliases"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_product_alias_key"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    printed_name: Mapped[str] = mapped_column(String(255), nullable=False)

    product: Mapped[Product] = relationship("Product", back_populates="aliases")
