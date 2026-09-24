import uuid

from app.core.config import get_settings
from app.domain.categories import UNCATEGORIZED, confident_category, match_rule
from app.models.line_item import LineItem
from app.models.receipt import Receipt
from app.ports.categorisation import ItemCategoriserPort
from app.repository.category import CategoryRepository
from app.repository.receipt import ReceiptRepository
from app.schemas.extraction import ExtractedLineItem


class CategorisationService:
    """Categorises stored line items: by the owner's hand, or by re-running the agent (C3, C4)."""

    def __init__(
        self,
        receipts: ReceiptRepository,
        categories: CategoryRepository,
        categoriser: ItemCategoriserPort | None = None,
    ) -> None:
        self.receipts = receipts
        self.categories = categories
        self.categoriser = categoriser

    async def reassign(
        self,
        item_id: uuid.UUID,
        category_id: uuid.UUID,
        user_id: uuid.UUID,
        apply_to_future: bool = False,
    ) -> LineItem:
        """File a line item under the category its owner chose, marked as manual.

        The manual flag is what `recategorise` respects (domain model invariant
        13). The categoriser's own confidence is left as it was: it records what
        the agent thought, which stays useful for auditing it.

        With `apply_to_future`, the choice is also remembered as a rule for later
        items with the same or a highly similar name from this merchant (C5).

        Raises NotFoundError for an item or category the user cannot see —
        another user's is reported exactly like a missing one (BRD N2).
        """
        # app.api.errors is imported late, as elsewhere in the services: importing
        # it at module level pulls in app.api's routers, which import this module.
        from app.api.errors import NotFoundError

        item = await self.receipts.get_line_item(item_id)
        if item is None:
            raise NotFoundError("Line item not found")
        category = await self.categories.get_available(category_id, user_id)
        if category is None:
            raise NotFoundError("Category not found")

        item.category_id = category.id
        item.category = category
        item.is_category_manual = True

        if apply_to_future:
            receipt = await self.receipts.get(item.receipt_id)
            assert receipt is not None  # the item was just found through its receipt
            await self.categories.save_rule(user_id, receipt.merchant_name, item.name, category.id)

        return item

    async def recategorise(self, receipt_id: uuid.UUID, user_id: uuid.UUID) -> Receipt:
        """Run the agent over a stored receipt again, leaving manual choices alone (C3, C4).

        Items the owner categorised by hand are never touched. The rest follow the
        upload order of precedence: a matching correction rule (C5) first, then
        the agent, whose confident answer is kept while anything else becomes
        Uncategorized.

        Raises NotFoundError for a receipt the user cannot see (BRD N2), and
        CategoriserUnavailableError when the agent placed nothing at all: the
        port cannot raise, so that is how an outage shows, and the receipt is
        left untouched rather than having every category wiped.
        """
        from app.api.errors import CategoriserUnavailableError, NotFoundError

        assert self.categoriser is not None
        receipt = await self.receipts.get_with_items(receipt_id)
        if receipt is None:
            raise NotFoundError("Receipt not found")

        automatic = [item for item in receipt.line_items if not item.is_category_manual]
        taxonomy = await self.categories.list_available(user_id)
        if not automatic or not taxonomy:
            return receipt

        by_id = {category.id: category for category in taxonomy}
        rules = await self.categories.list_rules(user_id)
        ruled = {
            item.id: by_id[chosen]
            for item in automatic
            if (chosen := match_rule(item.name, receipt.merchant_name, rules)) in by_id
        }
        for item in automatic:
            if item.id in ruled:
                item.category = ruled[item.id]
                # The user decided this, not a model: no score to report, and an
                # old low one must not keep flagging the item for review.
                item.category_confidence = None

        remaining = [item for item in automatic if item.id not in ruled]
        if not remaining:
            return receipt

        answers = await self.categoriser.categorise_items(
            [
                ExtractedLineItem(
                    name=item.name,
                    quantity=str(item.quantity),
                    unit_price=str(item.unit_price),
                    total_price=str(item.total_price),
                )
                for item in remaining
            ],
            taxonomy,
        )
        if all(answer.category_id is None for answer in answers):
            if ruled:
                return receipt
            raise CategoriserUnavailableError(
                "The categoriser gave no answer. Nothing was changed; try again later."
            )

        fallback = next((c for c in taxonomy if c.name == UNCATEGORIZED), None)
        threshold = get_settings().categorization_confidence_threshold
        for item, answer in zip(remaining, answers, strict=True):
            chosen = confident_category(answer.category_id, answer.category_confidence, threshold)
            category = by_id.get(chosen) if chosen else fallback
            if category is not None:
                item.category = category
            else:
                item.category_id = None
            item.category_confidence = answer.category_confidence
        return receipt
