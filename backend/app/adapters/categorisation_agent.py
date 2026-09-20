import json
import logging
import uuid
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from app.agent.core import Agent
from app.agent.types import Message
from app.models.category import Category
from app.ports.categorisation import ItemCategoriserPort
from app.schemas.extraction import ExtractedLineItem

logger = logging.getLogger(__name__)


class CategoryAssignment(BaseModel):
    """One line item's category as the model chose it, before validation."""

    item_index: int
    category_id: str | None
    category_name: str | None
    confidence: int

    model_config = ConfigDict(coerce_numbers_to_str=True)


class CategorisationResponse(BaseModel):
    """The model's answer for a whole receipt: one assignment per line item."""

    assignments: list[CategoryAssignment]


class ItemCategoriserAdapter(ItemCategoriserPort):
    """Assigns categories to extracted line items with an LLM (BRD C1).

    Sits behind `ItemCategoriserPort` so services never see the model, which is
    what lets the suite run the whole ingestion flow without network access.
    """

    def __init__(self, agent: Agent) -> None:
        self._agent = agent
        self.system_prompt = (
            "You are an expert spending categoriser. Your task is to assign exactly one "
            "category to each line item from a receipt.\n"
            "You will be given a list of available categories and a list of line items.\n"
            "For each line item, select the most appropriate category ID and Name.\n"
            "Also provide a confidence score between 0 and 100.\n"
            "If an item does not clearly fit any category, return null for the category "
            "and a low confidence score.\n"
        )

    async def categorise_items(
        self, items: list[ExtractedLineItem], categories: Sequence[Category]
    ) -> list[ExtractedLineItem]:
        """Fill in each item's category and confidence, in place (BRD C1).

        Mutates and returns the items it was given. An item the model declined
        to place, or placed in a category that was not on offer, comes back with
        `category_id` and `category_confidence` left as `None` — never as a
        confident guess, which is what BRD C3's review path depends on.

        Never raises: a categorisation failure returns the items untouched
        rather than losing a parsed receipt over a classification.
        """
        if not items or not categories:
            return items

        categories_by_id = {str(category.id): category for category in categories}
        categories_data = [
            {"id": category_id, "name": category.name}
            for category_id, category in categories_by_id.items()
        ]
        items_data = [
            {"index": i, "name": item.name, "total_price": item.total_price}
            for i, item in enumerate(items)
        ]

        prompt = (
            f"{self.system_prompt}\n\n"
            f"Available Categories:\n{json.dumps(categories_data, indent=2)}\n\n"
            f"Line Items to Categorise:\n{json.dumps(items_data, indent=2)}"
        )

        messages = [Message(role="user", content=[{"type": "text", "text": prompt}])]

        try:
            parsed = await self._agent.run_structured(
                messages, schema=CategorisationResponse, temperature=0.0
            )
        except Exception:
            logger.exception("Categorisation failed; leaving items uncategorised")
            return items

        assignments_by_index = {a.item_index: a for a in parsed.assignments}

        for index, item in enumerate(items):
            assignment = assignments_by_index.get(index)
            if assignment is None:
                continue
            self._apply(item, assignment, categories_by_id)

        return items

    @staticmethod
    def _apply(
        item: ExtractedLineItem,
        assignment: CategoryAssignment,
        categories_by_id: dict[str, Category],
    ) -> None:
        """Copy one assignment onto its item, discarding categories we never offered.

        A model is free to answer with an id that is well-formed but belongs to
        nothing, or to another user. Persisting that id would fail the foreign
        key and take the whole receipt down with it, so an unrecognised id is
        dropped and the item stays uncategorised. The name is taken from our own
        record rather than the model's reply, so the two can never disagree.
        """
        category = categories_by_id.get(assignment.category_id or "")
        if category is None:
            if assignment.category_id:
                logger.warning("Categoriser returned unknown category %s", assignment.category_id)
            return

        item.category_id = uuid.UUID(str(category.id))
        item.category_name = category.name
        item.category_confidence = assignment.confidence
