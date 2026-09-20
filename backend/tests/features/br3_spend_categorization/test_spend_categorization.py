# mypy: ignore-errors
"""Runs BR-3's Gherkin scenarios (F0.6.2).

C1 is live as of F5.2. The rest stay skipped until the epic that implements
them lands: C2/C3 with F5.3's threshold and review queue, C4/C5 with F5.4 and
F5.5's corrections, C6/C7 with F5.6's custom categories.
"""

import asyncio
import uuid
from unittest.mock import AsyncMock

import pytest
from pytest import FixtureRequest
from pytest_bdd import given, scenarios, then, when

from app.adapters.categorisation_agent import (
    CategorisationResponse,
    CategoryAssignment,
    ItemCategoriserAdapter,
)
from app.agent.core import Agent
from app.domain.categories import DEFAULT_CATEGORY_ORDER
from app.models.category import Category
from app.schemas.extraction import ExtractedLineItem

scenarios("spend_categorization.feature")


@pytest.fixture(autouse=True)
def skip_unimplemented(request: FixtureRequest) -> None:
    implemented = {"test_automatically_categorize_a_recognized_item"}
    if request.node.name not in implemented:
        pytest.skip("Awaiting F5.3-F5.6 spend categorization implementations")


@pytest.fixture
def taxonomy() -> list[Category]:
    """The seeded default categories, as F5.1 ships them."""
    return [Category(id=uuid.uuid4(), name=name) for name in DEFAULT_CATEGORY_ORDER]


@pytest.fixture
def agent() -> AsyncMock:
    """The categorising model, stubbed — a test that hits the network is not a test."""
    return AsyncMock(spec=Agent)


@pytest.fixture
def context() -> dict[str, object]:
    return {}


@given('a parsed receipt contains the item "Bananas 1kg"')
def parsed_receipt_with_bananas(context: dict[str, object]) -> None:
    context["items"] = [
        ExtractedLineItem(name="Bananas 1kg", quantity="1", unit_price="3.20", total_price="3.20")
    ]


@when("the agent categorizes the receipt")
def categorise_the_receipt(
    context: dict[str, object], agent: AsyncMock, taxonomy: list[Category]
) -> None:
    groceries = next(category for category in taxonomy if category.name == "Groceries")
    agent.run_structured.return_value = CategorisationResponse(
        assignments=[
            CategoryAssignment(
                item_index=0,
                category_id=str(groceries.id),
                category_name="Groceries",
                confidence=96,
            )
        ]
    )

    # pytest-bdd drives steps synchronously, so the port is awaited here rather
    # than by making the whole scenario async.
    context["result"] = asyncio.run(
        ItemCategoriserAdapter(agent).categorise_items(context["items"], taxonomy)
    )


@then('the item should be assigned to the "Groceries" category')
def item_is_groceries(context: dict[str, object], taxonomy: list[Category]) -> None:
    groceries = next(category for category in taxonomy if category.name == "Groceries")
    item = context["result"][0]
    assert item.category_id == groceries.id
    assert item.category_name == "Groceries"


@then("the categorization confidence should be recorded")
def confidence_is_recorded(context: dict[str, object]) -> None:
    assert context["result"][0].category_confidence == 96
