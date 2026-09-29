import asyncio
import uuid
from unittest.mock import AsyncMock

import pytest

from app.adapters.goal_mapping_agent import GoalMappingAdapter, GoalMappingResponse
from app.agent.core import Agent
from app.models.category import Category


@pytest.fixture
def mock_agent() -> AsyncMock:
    return AsyncMock(spec=Agent)


@pytest.fixture
def adapter(mock_agent: AsyncMock) -> GoalMappingAdapter:
    return GoalMappingAdapter(agent=mock_agent)


@pytest.fixture
def categories() -> list[Category]:
    return [
        Category(id=uuid.uuid4(), name="Groceries", user_id=uuid.uuid4()),
        Category(id=uuid.uuid4(), name="Dining", user_id=uuid.uuid4()),
    ]


@pytest.mark.asyncio
async def test_the_models_choice_becomes_the_goals_watched_lines(
    adapter: GoalMappingAdapter, mock_agent: AsyncMock, categories: list[Category]
) -> None:
    mock_agent.run_structured.return_value = GoalMappingResponse(
        mapped_category_ids=[str(categories[0].id)], mapped_item_names=["sweets", "fast food"]
    )

    result = await adapter.map_goal("eat healthier", "no more sugar", categories)

    assert len(result.mapped_category_ids) == 1
    assert result.mapped_category_ids[0] == categories[0].id
    assert result.mapped_item_names == ["sweets", "fast food"]


@pytest.mark.asyncio
async def test_a_category_we_never_offered_is_refused(
    adapter: GoalMappingAdapter, mock_agent: AsyncMock, categories: list[Category]
) -> None:
    mock_agent.run_structured.return_value = GoalMappingResponse(
        mapped_category_ids=[str(uuid.uuid4())], mapped_item_names=["sweets"]
    )

    result = await adapter.map_goal("eat healthier", None, categories)

    assert result.mapped_category_ids == []
    assert result.mapped_item_names == ["sweets"]


@pytest.mark.asyncio
async def test_nothing_is_asked_of_the_model_when_there_are_no_categories(
    adapter: GoalMappingAdapter, mock_agent: AsyncMock
) -> None:
    result = await adapter.map_goal("eat healthier", None, [])
    assert result.mapped_category_ids == []
    assert result.mapped_item_names == []
    mock_agent.run_structured.assert_not_called()


@pytest.mark.asyncio
async def test_a_failing_model_returns_empty_mapping(
    adapter: GoalMappingAdapter, mock_agent: AsyncMock, categories: list[Category]
) -> None:
    mock_agent.run_structured.side_effect = Exception("API Error")

    result = await adapter.map_goal("eat healthier", None, categories)

    assert result.mapped_category_ids == []
    assert result.mapped_item_names == []


@pytest.mark.asyncio
async def test_the_models_answer_is_tidied_before_it_is_kept(
    adapter: GoalMappingAdapter, mock_agent: AsyncMock, categories: list[Category]
) -> None:
    offered = str(categories[0].id)
    mock_agent.run_structured.return_value = GoalMappingResponse(
        mapped_category_ids=[offered, offered],
        mapped_item_names=["Sweets", "sweets ", "", "x" * 300],
    )

    result = await adapter.map_goal("eat healthier", None, categories)

    assert result.mapped_category_ids == [categories[0].id]
    assert result.mapped_item_names == ["sweets", "x" * 120]


@pytest.mark.asyncio
async def test_a_model_too_slow_to_answer_leaves_the_mapping_empty(
    mock_agent: AsyncMock, categories: list[Category]
) -> None:
    """The user is waiting on the save, so a hung model must not hold it."""

    async def hang(*_: object, **__: object) -> None:
        await asyncio.sleep(10)

    mock_agent.run_structured.side_effect = hang
    adapter = GoalMappingAdapter(agent=mock_agent, timeout_seconds=0.01)

    result = await adapter.map_goal("eat healthier", None, categories)

    assert (result.mapped_category_ids, result.mapped_item_names) == ([], [])
