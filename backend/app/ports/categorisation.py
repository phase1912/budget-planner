from collections.abc import Sequence
from typing import Protocol

from app.models.category import Category
from app.schemas.extraction import ExtractedLineItem


class ItemCategoriserPort(Protocol):
    """Assigns a spending category to each extracted line item (BRD C1)."""

    async def categorise_items(
        self,
        items: list[ExtractedLineItem],
        categories: Sequence[Category],
    ) -> list[ExtractedLineItem]:
        """Fill in `category_id`, `category_name` and `category_confidence` per item.

        Implementations mutate and return the items they were given, choosing
        only from `categories`. An item that cannot be placed comes back with
        those three fields left as `None` rather than as a confident guess,
        which is what BRD C3's review path reads.

        Must not raise: a categorisation failure leaves the items untouched, so
        a parsed receipt is never lost over a classification.
        """
        ...
