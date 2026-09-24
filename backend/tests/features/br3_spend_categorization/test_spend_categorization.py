# mypy: ignore-errors
"""Runs BR-3's Gherkin scenarios (F0.6.2).

C1 is live as of F5.2, C2/C3 as of F5.3, C4/C5 as of F5.4/F5.5. C6/C7 stay
skipped until F5.6's custom categories land.
"""

import asyncio
import uuid
from datetime import UTC, datetime
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
from app.domain.categories import DEFAULT_CATEGORY_ORDER, UNCATEGORIZED, normalise_name
from app.models.category import Category
from app.models.category_rule import CategoryRule
from app.models.line_item import LineItem
from app.models.receipt import Receipt
from app.schemas.extraction import ExtractedLineItem
from app.schemas.receipt import LineItemResponse
from app.services.categorisation import CategorisationService
from app.services.receipt import ReceiptService

scenarios("spend_categorization.feature")


@pytest.fixture(autouse=True)
def skip_unimplemented(request: FixtureRequest) -> None:
    implemented = {
        "test_automatically_categorize_a_recognized_item",
        "test_fallback_to_uncategorized_for_unrecognized_item",
        "test_user_corrects_a_category_and_agent_learns_from_it",
    }
    if request.node.name not in implemented:
        pytest.skip("Awaiting F5.6 custom categories")


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


class _InMemoryReceipts:
    """Just enough of `ReceiptRepository` for a reassignment: one receipt, one item."""

    def __init__(self, receipt: Receipt, item: LineItem) -> None:
        self.receipt, self.item = receipt, item

    async def get_line_item(self, item_id: uuid.UUID) -> LineItem | None:
        return self.item if item_id == self.item.id else None

    async def get(self, receipt_id: uuid.UUID) -> Receipt | None:
        return self.receipt if receipt_id == self.receipt.id else None


class _InMemoryCategories:
    """Just enough of `CategoryRepository`: the taxonomy plus a rule store."""

    def __init__(self, taxonomy: list[Category]) -> None:
        self.taxonomy = taxonomy
        self.rules: list[CategoryRule] = []

    async def get_available(self, category_id: uuid.UUID, user_id: uuid.UUID) -> Category | None:
        return next((c for c in self.taxonomy if c.id == category_id), None)

    async def save_rule(
        self, user_id: uuid.UUID, merchant_name: str | None, item_name: str, category_id: uuid.UUID
    ) -> CategoryRule:
        rule = CategoryRule(
            user_id=user_id,
            merchant_name=normalise_name(merchant_name),
            item_name=normalise_name(item_name),
            category_id=category_id,
            created_at=datetime.now(UTC),
        )
        self.rules.append(rule)
        return rule

    async def list_rules(self, user_id: uuid.UUID) -> list[CategoryRule]:
        return self.rules


def _named(taxonomy: list[Category], name: str) -> Category:
    return next(category for category in taxonomy if category.name == name)


@given('the item "Protein Bar XL" was categorized as "Groceries"')
def protein_bar_categorized_as_groceries(
    context: dict[str, object], taxonomy: list[Category]
) -> None:
    receipt = Receipt(id=uuid.uuid4(), user_id=uuid.uuid4(), merchant_name="Fresh Market")
    groceries = _named(taxonomy, "Groceries")
    context["receipt"] = receipt
    context["item"] = LineItem(
        id=uuid.uuid4(),
        receipt_id=receipt.id,
        name="Protein Bar XL",
        category_id=groceries.id,
        category=groceries,
        category_confidence=82,
        is_category_manual=False,
    )


@when('the user reassigns it to "Health"')
def user_reassigns_to_health(context: dict[str, object], taxonomy: list[Category]) -> None:
    categories = _InMemoryCategories(taxonomy)
    service = CategorisationService(
        _InMemoryReceipts(context["receipt"], context["item"]), categories
    )
    asyncio.run(
        service.reassign(
            context["item"].id,
            _named(taxonomy, "Health").id,
            context["receipt"].user_id,
            apply_to_future=True,
        )
    )
    context["categories"] = categories


@then("the agent should update the category for that item")
def item_is_filed_under_health(context: dict[str, object], taxonomy: list[Category]) -> None:
    assert context["item"].category_id == _named(taxonomy, "Health").id
    assert context["item"].is_category_manual is True


@then(
    'future receipts from the same merchant with the same item name should be categorized as "Health"'  # noqa: E501
)
def future_receipts_categorized_as_health(
    context: dict[str, object], agent: AsyncMock, taxonomy: list[Category]
) -> None:
    # The agent would still call it Groceries; the user's rule must win (precedence, C5).
    agent.run_structured.return_value = CategorisationResponse(
        assignments=[
            CategoryAssignment(
                item_index=0,
                category_id=str(_named(taxonomy, "Groceries").id),
                category_name="Groceries",
                confidence=99,
            )
        ]
    )
    service = ReceiptService(categoriser_port=ItemCategoriserAdapter(agent))
    rules = asyncio.run(context["categories"].list_rules(context["receipt"].user_id))
    extraction = {
        "merchant_name": "Fresh Market",
        "line_items": [
            {"name": "Protein Bar XL", "quantity": "1", "unit_price": "2.50", "total_price": "2.50"}
        ],
    }

    asyncio.run(service._categorise_extraction(extraction, taxonomy, rules))

    assert extraction["line_items"][0]["category_name"] == "Health"
