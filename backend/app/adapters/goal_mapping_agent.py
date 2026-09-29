import asyncio
import json
import logging
import uuid
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from app.agent.core import Agent
from app.agent.types import Message
from app.domain.goals import WATCHED_LINES_MAX, clean_item_names
from app.models.category import Category
from app.ports.goal_mapping import GoalMapperPort, GoalMappingResult

logger = logging.getLogger(__name__)


class GoalMappingResponse(BaseModel):
    """The model's answer for translating a lifestyle goal into spending lines."""

    mapped_category_ids: list[str] = Field(
        description="The IDs of the categories that should be monitored."
    )
    mapped_item_names: list[str] = Field(
        description=(
            "A list of specific line-item names (e.g., 'sweets', 'alcohol') "
            "that relate to the goal."
        )
    )

    model_config = ConfigDict(coerce_numbers_to_str=True)


class GoalMappingAdapter(GoalMapperPort):
    """Translates a non-financial goal into specific spending lines using an LLM (BRD F8.2).

    Sits behind `GoalMapperPort` so services never see the model directly.
    `timeout_seconds` bounds the whole call, retries included, because the user
    is waiting on the save that asked for it.
    """

    def __init__(self, agent: Agent, timeout_seconds: float = 20.0) -> None:
        self._agent = agent
        self._timeout_seconds = timeout_seconds
        self.system_prompt = (
            "You are a financial advisor agent. Your task is to translate a lifestyle goal "
            "(e.g., 'lose weight', 'eat healthier', 'reduce carbon footprint') into specific "
            "spending categories and specific recurring item names to monitor.\n"
            "You will be given a list of available categories and the details of the goal.\n"
            "Return a list of category IDs that broadly match the goal, and a list of specific "
            "line-item names or keywords that represent spending against this goal (e.g. 'snacks', "
            "'sugary drinks', 'fast food'). Keep the item names lowercase and concise."
        )

    async def map_goal(
        self,
        name: str,
        description: str | None,
        categories: Sequence[Category],
    ) -> GoalMappingResult:
        """Choose the categories and item names a lifestyle goal watches (BRD F9).

        Only categories on offer come back, each once; item names are tidied by
        `clean_item_names`. Never raises: a failed or slow model yields an empty
        mapping, which the user can fill in by hand, rather than a lost goal.
        """
        if not categories:
            return GoalMappingResult(mapped_category_ids=[], mapped_item_names=[])

        categories_by_id = {str(category.id): category for category in categories}
        categories_data = [
            {"id": category_id, "name": category.name}
            for category_id, category in categories_by_id.items()
        ]

        prompt = (
            f"{self.system_prompt}\n\n"
            f"Available Categories:\n{json.dumps(categories_data, indent=2)}\n\n"
            f"Goal Name: {name}\n"
        )
        if description:
            prompt += f"Goal Description: {description}\n"

        messages = [Message(role="user", content=[{"type": "text", "text": prompt}])]

        try:
            async with asyncio.timeout(self._timeout_seconds):
                parsed = await self._agent.run_structured(
                    messages, schema=GoalMappingResponse, temperature=0.0
                )
        except Exception:
            logger.exception("Goal mapping failed; returning empty mapping")
            return GoalMappingResult(mapped_category_ids=[], mapped_item_names=[])

        category_ids: list[uuid.UUID] = []
        for category_id in parsed.mapped_category_ids:
            category = categories_by_id.get(category_id)
            if category is None:
                logger.warning("Goal mapper returned unknown category %s", category_id)
            elif category.id not in category_ids:
                category_ids.append(category.id)

        return GoalMappingResult(
            mapped_category_ids=category_ids[:WATCHED_LINES_MAX],
            mapped_item_names=clean_item_names(parsed.mapped_item_names),
        )
