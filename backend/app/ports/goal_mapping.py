import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from app.models.category import Category


@dataclass(frozen=True)
class GoalMappingResult:
    """The outcome of translating a lifestyle goal into financial targets (BRD F8.2)."""

    mapped_category_ids: list[uuid.UUID]
    mapped_item_names: list[str]


class GoalMapperPort(Protocol):
    """Translates a non-financial goal into specific spending lines (BRD F9, F8.2)."""

    async def map_goal(
        self,
        name: str,
        description: str | None,
        categories: Sequence[Category],
    ) -> GoalMappingResult:
        """Decide which categories and items a lifestyle goal should watch.

        A financial goal already knows what it limits; a lifestyle goal (like
        'lose weight') must be projected onto spending to be tracked. Returns
        only categories from `categories`. Never raises: when no answer can be
        had, the mapping is empty and the user fills it in by hand.
        """
        ...
