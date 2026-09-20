import json
import logging

from pydantic import BaseModel, ConfigDict

from app.agent.core import Agent
from app.agent.types import Message
from app.models.category import Category
from app.ports.categorisation import ItemCategoriserPort
from app.schemas.extraction import ExtractedLineItem

logger = logging.getLogger(__name__)


class CategoryAssignment(BaseModel):
    item_index: int
    category_id: str | None
    category_name: str | None
    confidence: int

    model_config = ConfigDict(coerce_numbers_to_str=True)


class CategorisationResponse(BaseModel):
    assignments: list[CategoryAssignment]


class ItemCategoriserAdapter(ItemCategoriserPort):

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
        self, items: list[ExtractedLineItem], categories: list[Category]
    ) -> list[ExtractedLineItem]:
        if not items or not categories:
            return items

        categories_data = [{"id": str(cat.id), "name": cat.name} for cat in categories]
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

            assignments_by_index = {a.item_index: a for a in parsed.assignments}

            for i, item in enumerate(items):
                assignment = assignments_by_index.get(i)
                if assignment:
                    try:
                        import uuid

                        item.category_id = (
                            uuid.UUID(assignment.category_id) if assignment.category_id else None
                        )
                    except ValueError:
                        item.category_id = None
                    item.category_name = assignment.category_name
                    item.category_confidence = assignment.confidence

            return items

        except Exception as e:
            logger.error(f"Categorisation failed: {e}")
            return items
