import uuid
from unittest.mock import AsyncMock

import pytest

from app.adapters.categorisation_agent import ItemCategoriserAdapter
from app.agent.core import Agent
from app.models.category import Category
from app.schemas.extraction import ExtractedLineItem


@pytest.fixture
def mock_agent() -> AsyncMock:
    return AsyncMock(spec=Agent)


@pytest.fixture
def adapter(mock_agent: AsyncMock) -> ItemCategoriserAdapter:
    return ItemCategoriserAdapter(agent=mock_agent)


@pytest.mark.asyncio
async def test_categorise_items_success(
    adapter: ItemCategoriserAdapter, mock_agent: AsyncMock
) -> None:
    cat_id1 = uuid.uuid4()
    cat_id2 = uuid.uuid4()
    categories = [Category(id=cat_id1, name="Groceries"), Category(id=cat_id2, name="Dining")]
    items = [
        ExtractedLineItem(name="Milk", quantity="1", unit_price="2.0", total_price="2.0"),
        ExtractedLineItem(name="Restaurant Tip", quantity="1", unit_price="5.0", total_price="5.0"),
    ]

    # Mock structured response
    from app.adapters.categorisation_agent import CategorisationResponse, CategoryAssignment

    mock_response = CategorisationResponse(
        assignments=[
            CategoryAssignment(
                item_index=0, category_id=str(cat_id1), category_name="Groceries", confidence=95
            ),
            CategoryAssignment(
                item_index=1, category_id=str(cat_id2), category_name="Dining", confidence=88
            ),
        ]
    )
    mock_agent.run_structured.return_value = mock_response

    result = await adapter.categorise_items(items, categories)

    assert len(result) == 2
    assert result[0].category_id == cat_id1
    assert result[0].category_name == "Groceries"
    assert result[0].category_confidence == 95

    assert result[1].category_id == cat_id2
    assert result[1].category_name == "Dining"
    assert result[1].category_confidence == 88


@pytest.mark.asyncio
async def test_categorise_items_empty(
    adapter: ItemCategoriserAdapter, mock_agent: AsyncMock
) -> None:
    result = await adapter.categorise_items([], [])
    assert result == []
    mock_agent.run_structured.assert_not_called()


@pytest.mark.asyncio
async def test_categorise_items_agent_error(
    adapter: ItemCategoriserAdapter, mock_agent: AsyncMock
) -> None:
    categories = [Category(id=uuid.uuid4(), name="Groceries")]
    items = [ExtractedLineItem(name="Milk", quantity="1", unit_price="2.0", total_price="2.0")]

    mock_agent.run_structured.side_effect = Exception("API Error")

    result = await adapter.categorise_items(items, categories)

    assert len(result) == 1
    # Ensure it returns gracefully without modifications
    assert result[0].category_id is None
    assert result[0].category_confidence == 100  # default
