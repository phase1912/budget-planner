import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductVariantResponse(BaseModel):
    """One way a product is printed, and how often it was bought under it (F16.1)."""

    alias_id: uuid.UUID
    printed_name: str
    purchases: int

    model_config = ConfigDict(from_attributes=True)


class CheaperShopResponse(BaseModel):
    """Where a product recently cost less than where it was last bought (F16.3).

    `difference` is for one item — every purchase of a product is one size — and `percent`
    is of the price at `instead_of`.
    """

    shop: str
    instead_of: str
    difference: Decimal
    percent: Decimal | None


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
    cheaper: CheaperShopResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class MergeProductsRequest(BaseModel):
    """Other products to fold into the one in the path; it keeps its name (F16.1)."""

    product_ids: list[uuid.UUID] = Field(min_length=1, max_length=50)


class SplitProductRequest(BaseModel):
    """The way of printing to take out of the product into one of its own (F16.1)."""

    alias_id: uuid.UUID


class AmountsResponse(BaseModel):
    """How much was bought: times, money, and quantity by kind — `pc`, `g` or `ml` (F16.2)."""

    times: int
    spent: Decimal
    quantities: dict[str, Decimal]


class PricePointResponse(BaseModel):
    """What one purchase cost a unit, and per kg or l where the size is known."""

    day: date
    shop: str | None
    unit_price: Decimal
    base_price: Decimal | None


class PriceChangeResponse(BaseModel):
    """The move from the first purchase's price to the last, per kg/l where known."""

    first: Decimal
    last: Decimal
    difference: Decimal
    percent: Decimal | None


class ShopPriceResponse(BaseModel):
    """A product's price in one shop, and how much above the cheapest shop it is (F16.2.2)."""

    shop: str
    purchases: int
    average: Decimal
    latest: Decimal
    latest_day: date
    above_cheapest: Decimal
    above_percent: Decimal | None


class ProductFactsResponse(BaseModel):
    """A selected product's identity and size."""

    id: uuid.UUID
    name: str
    size_amount: Decimal | None
    size_unit: str | None


class ProductPurchasesResponse(BaseModel):
    """One selected product over the period: amounts, prices, change and shops."""

    product: ProductFactsResponse
    amounts: AmountsResponse
    prices: list[PricePointResponse]
    change: PriceChangeResponse | None
    shops: list[ShopPriceResponse]


class MonthPurchasesResponse(BaseModel):
    """The selection's purchases in one calendar month (`month` is its first day)."""

    month: date
    amounts: AmountsResponse


class ExplorationResponse(BaseModel):
    """What a selection of products was bought, over a period and month by month (F16.2)."""

    totals: AmountsResponse
    months: list[MonthPurchasesResponse]
    products: list[ProductPurchasesResponse]


class SelectionRequest(BaseModel):
    """Products to keep together under a name (F16.2)."""

    name: str = Field(min_length=1, max_length=60)
    product_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)


class SelectionResponse(BaseModel):
    """A saved selection of products."""

    id: uuid.UUID
    name: str
    product_ids: list[uuid.UUID]

    model_config = ConfigDict(from_attributes=True)
