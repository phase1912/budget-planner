import uuid
from unittest.mock import AsyncMock

import pytest

from app.adapters.categorisation_agent import (
    CategorisationResponse,
    CategoryAssignment,
    ItemCategoriserAdapter,
)
from app.agent.core import Agent
from app.models.category import Category
from app.schemas.extraction import ExtractedLineItem


@pytest.fixture
def mock_agent() -> AsyncMock:
    """An `Agent` that answers whatever a test tells it to, without a network."""
    return AsyncMock(spec=Agent)


@pytest.fixture
def adapter(mock_agent: AsyncMock) -> ItemCategoriserAdapter:
    return ItemCategoriserAdapter(agent=mock_agent)


@pytest.fixture
def categories() -> list[Category]:
    return [
        Category(id=uuid.uuid4(), name="Groceries"),
        Category(id=uuid.uuid4(), name="Dining"),
    ]


def _item(name: str) -> ExtractedLineItem:
    return ExtractedLineItem(name=name, quantity="1", unit_price="2.0", total_price="2.0")


@pytest.mark.asyncio
async def test_each_item_takes_the_category_the_model_chose(
    adapter: ItemCategoriserAdapter, mock_agent: AsyncMock, categories: list[Category]
) -> None:
    """The happy path: every line item comes back filed and scored (BRD C1)."""
    items = [_item("Milk"), _item("Restaurant Tip")]
    mock_agent.run_structured.return_value = CategorisationResponse(
        assignments=[
            CategoryAssignment(
                item_index=0,
                category_id=str(categories[0].id),
                category_name="Groceries",
                confidence=95,
            ),
            CategoryAssignment(
                item_index=1,
                category_id=str(categories[1].id),
                category_name="Dining",
                confidence=88,
            ),
        ]
    )

    result = await adapter.categorise_items(items, categories)

    assert [(i.category_id, i.category_name, i.category_confidence) for i in result] == [
        (categories[0].id, "Groceries", 95),
        (categories[1].id, "Dining", 88),
    ]


@pytest.mark.asyncio
async def test_a_category_we_never_offered_is_refused(
    adapter: ItemCategoriserAdapter, mock_agent: AsyncMock, categories: list[Category]
) -> None:
    """A well-formed id for a category that does not exist would break the FK on save."""
    items = [_item("Milk")]
    mock_agent.run_structured.return_value = CategorisationResponse(
        assignments=[
            CategoryAssignment(
                item_index=0,
                category_id=str(uuid.uuid4()),
                category_name="Invented",
                confidence=99,
            )
        ]
    )

    result = await adapter.categorise_items(items, categories)

    assert result[0].category_id is None
    assert result[0].category_name is None
    assert result[0].category_confidence is None


@pytest.mark.asyncio
async def test_a_malformed_category_id_is_refused(
    adapter: ItemCategoriserAdapter, mock_agent: AsyncMock, categories: list[Category]
) -> None:
    """Nothing that is not one of our ids reaches the database."""
    items = [_item("Milk")]
    mock_agent.run_structured.return_value = CategorisationResponse(
        assignments=[
            CategoryAssignment(
                item_index=0, category_id="not-a-uuid", category_name="Groceries", confidence=99
            )
        ]
    )

    result = await adapter.categorise_items(items, categories)

    assert result[0].category_id is None
    assert result[0].category_confidence is None


@pytest.mark.asyncio
async def test_the_name_comes_from_our_record_not_the_models_reply(
    adapter: ItemCategoriserAdapter, mock_agent: AsyncMock, categories: list[Category]
) -> None:
    """A model that pairs a real id with the wrong name must not rename the category."""
    items = [_item("Milk")]
    mock_agent.run_structured.return_value = CategorisationResponse(
        assignments=[
            CategoryAssignment(
                item_index=0,
                category_id=str(categories[0].id),
                category_name="Dining",
                confidence=91,
            )
        ]
    )

    result = await adapter.categorise_items(items, categories)

    assert result[0].category_name == "Groceries"


@pytest.mark.asyncio
async def test_an_item_the_model_skipped_stays_uncategorised(
    adapter: ItemCategoriserAdapter, mock_agent: AsyncMock, categories: list[Category]
) -> None:
    """A missing assignment is an absence of a decision, not a confident one (BRD C3)."""
    items = [_item("Milk"), _item("Obscure Thing")]
    mock_agent.run_structured.return_value = CategorisationResponse(
        assignments=[
            CategoryAssignment(
                item_index=0,
                category_id=str(categories[0].id),
                category_name="Groceries",
                confidence=95,
            )
        ]
    )

    result = await adapter.categorise_items(items, categories)

    assert result[1].category_id is None
    assert result[1].category_confidence is None


@pytest.mark.asyncio
async def test_nothing_is_asked_of_the_model_when_there_is_nothing_to_file(
    adapter: ItemCategoriserAdapter, mock_agent: AsyncMock
) -> None:
    """No items, or no categories to choose from, means no call at all."""
    assert await adapter.categorise_items([], []) == []
    mock_agent.run_structured.assert_not_called()


@pytest.mark.asyncio
async def test_a_failing_model_leaves_the_receipt_intact(
    adapter: ItemCategoriserAdapter, mock_agent: AsyncMock, categories: list[Category]
) -> None:
    """A categorisation outage must not cost the user a parsed receipt."""
    items = [_item("Milk")]
    mock_agent.run_structured.side_effect = Exception("API Error")

    result = await adapter.categorise_items(items, categories)

    assert len(result) == 1
    assert result[0].category_id is None
    assert result[0].category_confidence is None
