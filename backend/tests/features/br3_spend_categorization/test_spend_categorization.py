# mypy: ignore-errors
"""Runs BR-3's Gherkin scenarios (F0.6.2).

C1 is live as of F5.2, C2/C3 as of F5.3. The rest stay skipped until the
epic that implements them lands: C4/C5 with F5.4 and F5.5's corrections,
C6/C7 with F5.6's custom categories.
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
from app.domain.categories import DEFAULT_CATEGORY_ORDER, UNCATEGORIZED
from app.models.category import Category
from app.schemas.extraction import ExtractedLineItem
from app.schemas.receipt import LineItemResponse
from app.services.receipt import ReceiptService

scenarios("spend_categorization.feature")


@pytest.fixture(autouse=True)
def skip_unimplemented(request: FixtureRequest) -> None:
    implemented = {
        "test_automatically_categorize_a_recognized_item",
        "test_fallback_to_uncategorized_for_unrecognized_item",
    }
    if request.node.name not in implemented:
        pytest.skip("Awaiting F5.4-F5.6 spend categorization implementations")


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


@given("a parsed receipt contains an item with an ambiguous or unknown name")
def parsed_receipt_with_unknown_item(context: dict[str, object]) -> None:
    context["extraction"] = {
        "line_items": [
            {"name": "XJ-42 SKU", "quantity": "1", "unit_price": "20.70", "total_price": "20.70"}
        ]
    }


@when("the agent attempts to categorize it")
def agent_attempts_to_categorise(context: dict[str, object], agent: AsyncMock) -> None:
    context["categoriser"] = ItemCategoriserAdapter(agent)


@when("the categorization confidence is below the threshold")
def confidence_below_threshold(
    context: dict[str, object], agent: AsyncMock, taxonomy: list[Category]
) -> None:
    groceries = next(category for category in taxonomy if category.name == "Groceries")
    agent.run_structured.return_value = CategorisationResponse(
        assignments=[
            CategoryAssignment(
                item_index=0,
                category_id=str(groceries.id),
                category_name="Groceries",
                confidence=40,
            )
        ]
    )
    service = ReceiptService(categoriser_port=context["categoriser"])
    asyncio.run(service._categorise_extraction(context["extraction"], taxonomy))
    context["item"] = context["extraction"]["line_items"][0]


@then('the item should be assigned to "Uncategorized"')
def item_is_uncategorized(context: dict[str, object], taxonomy: list[Category]) -> None:
    uncategorized = next(category for category in taxonomy if category.name == UNCATEGORIZED)
    assert context["item"]["category_id"] == str(uncategorized.id)
    assert context["item"]["category_name"] == UNCATEGORIZED


@then("flagged for user review")
def item_is_flagged_for_review(context: dict[str, object]) -> None:
    item = context["item"]
    response = LineItemResponse(
        id=uuid.uuid4(),
        name=item["name"],
        quantity=item["quantity"],
        unit_price=item["unit_price"],
        total_price=item["total_price"],
        category_id=item["category_id"],
        category_confidence=item["category_confidence"],
    )
    assert response.category_is_low_confidence
