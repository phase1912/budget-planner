from typing import Protocol

from app.models.category import Category
from app.schemas.extraction import ExtractedLineItem


class ItemCategoriserPort(Protocol):
    """Protocol for assigning categories to extracted line items."""

    async def categorise_items(
        self,
        items: list[ExtractedLineItem],
        categories: list[Category],
    ) -> list[ExtractedLineItem]:
        """Assign a category to each line item.

        Returns a new list of `ExtractedLineItem` with `category_id`,
        `category_name`, and `category_confidence` fields populated.
        """
        ...
