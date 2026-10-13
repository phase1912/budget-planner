import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductVariantResponse(BaseModel):
    """One way a product is printed, and how often it was bought under it (F16.1)."""

    alias_id: uuid.UUID
    printed_name: str
    purchases: int

    model_config = ConfigDict(from_attributes=True)


class ProductResponse(BaseModel):
    """A product the user buys, as the products list shows it (F16.1).

    The size is in grams (`g`) or millilitres (`ml`), when the receipt printed one.
    """

    id: uuid.UUID
    name: str
    size_amount: Decimal | None
    size_unit: str | None
    purchases: int
    shops: int
    last_bought: datetime | None
    spent: Decimal
    variants: list[ProductVariantResponse]

    model_config = ConfigDict(from_attributes=True)


class MergeProductsRequest(BaseModel):
    """Other products to fold into the one in the path; it keeps its name (F16.1)."""

    product_ids: list[uuid.UUID] = Field(min_length=1, max_length=50)


class SplitProductRequest(BaseModel):
    """The way of printing to take out of the product into one of its own (F16.1)."""

    alias_id: uuid.UUID
