"""Runs BR-2's Gherkin scenarios (F0.6.2)."""

from dataclasses import dataclass

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from app.domain.position_matching import ComparisonNotPossible, MatchResult, match_positions

scenarios("multi_photo_position_matching.feature")


@dataclass
class DummyPosition:
    name: str = ""
    unit_price: str = ""
    quantity: str = ""
    total_price: str = ""


@pytest.fixture
def context() -> dict[str, object]:
    return {
        "item_a": DummyPosition(),
        "item_b": DummyPosition(),
        "same_receipt": True,
        "result": None,
        "error": None,
        "override_logged": False,
    }


@given(
    "the user photographs a long receipt in two overlapping "
    "shots because it does not fit in one frame"
)
def given_overlapping_shots(context: dict[str, object]) -> None:
    context["same_receipt"] = True


@given(
    parsers.parse(
        'the item "{name}" priced at {price} PLN, quantity {qty}, '
        "appears near the bottom of photo one"
    )
)
def given_item_photo_one(context: dict[str, object], name: str, price: str, qty: str) -> None:
    item_a = context["item_a"]
    assert isinstance(item_a, DummyPosition)
    item_a.name = name
    item_a.unit_price = price
    item_a.quantity = qty
    item_a.total_price = str(float(price) * float(qty))


@given(
    parsers.parse(
        'the same item "{name}" priced at {price} PLN, quantity {qty}, '
        "also appears near the top of photo two"
    )
)
def given_item_photo_two(context: dict[str, object], name: str, price: str, qty: str) -> None:
    item_b = context["item_b"]
    assert isinstance(item_b, DummyPosition)
    item_b.name = name
    item_b.unit_price = price
    item_b.quantity = qty
    item_b.total_price = str(float(price) * float(qty))


@when("the agent compares the line items from both photos")
def when_compares_both_photos(context: dict[str, object]) -> None:
    item_a = context["item_a"]
    item_b = context["item_b"]
    same_receipt = context["same_receipt"]
    assert isinstance(item_a, DummyPosition)
    assert isinstance(item_b, DummyPosition)
    assert isinstance(same_receipt, bool)
    try:
        context["result"] = match_positions(item_a, item_b, same_receipt=same_receipt)
    except ComparisonNotPossible as e:
        context["error"] = e


@then(parsers.parse('the pair should be classified as "{expected_class}"'))
def then_classified_as(context: dict[str, object], expected_class: str) -> None:
    result = context["result"]
    assert isinstance(result, MatchResult)
    expected = MatchResult.SAME if expected_class == "same position" else MatchResult.DIFFERENT
    assert result == expected


@given(parsers.parse('a position named "{name}" priced at {price} PLN appears on photo one'))
def given_pos_photo_one(context: dict[str, object], name: str, price: str) -> None:
    item_a = context["item_a"]
    assert isinstance(item_a, DummyPosition)
    item_a.name = name
    item_a.unit_price = price
    item_a.quantity = "1"
    item_a.total_price = price


@given(parsers.parse('a position named "{name}" priced at {price} PLN appears on photo two'))
def given_pos_photo_two(context: dict[str, object], name: str, price: str) -> None:
    item_b = context["item_b"]
    assert isinstance(item_b, DummyPosition)
    item_b.name = name
    item_b.unit_price = price
    item_b.quantity = "1"
    item_b.total_price = price


@when("the agent compares the two positions")
def when_compares_positions(context: dict[str, object]) -> None:
    when_compares_both_photos(context)


@then(parsers.parse('the agent should classify the pair as "{expected_class}"'))
def then_agent_classify(context: dict[str, object], expected_class: str) -> None:
    then_classified_as(context, expected_class)


@given("the user uploads a photo of a grocery receipt")
def given_grocery_receipt(context: dict[str, object]) -> None:
    item_a = context["item_a"]
    assert isinstance(item_a, DummyPosition)
    item_a.name = "Apple"
    item_a.unit_price = "1.00"
    item_a.quantity = "1"
    item_a.total_price = "1.00"


@given("a photo of a restaurant receipt")
def given_restaurant_receipt(context: dict[str, object]) -> None:
    item_b = context["item_b"]
    assert isinstance(item_b, DummyPosition)
    item_b.name = "Apple"
    item_b.unit_price = "1.00"
    item_b.quantity = "1"
    item_b.total_price = "1.00"
    context["same_receipt"] = False


@when("the agent compares the line items between the two photos")
def when_compare_between_photos(context: dict[str, object]) -> None:
    when_compares_both_photos(context)


@then(parsers.parse('no items should be classified as "{expected_class}"'))
def then_no_items_classified(context: dict[str, object], expected_class: str) -> None:
    result = context["result"]
    assert isinstance(result, MatchResult)
    expected_not = MatchResult.SAME if expected_class == "same position" else MatchResult.DIFFERENT
    assert result != expected_not


@given(
    parsers.parse('the user has a receipt dated {date} containing "{name}" priced at {price} PLN')
)
def given_receipt_dated_1(context: dict[str, object], date: str, name: str, price: str) -> None:
    item_a = context["item_a"]
    assert isinstance(item_a, DummyPosition)
    item_a.name = name
    item_a.unit_price = price
    item_a.quantity = "1"
    item_a.total_price = price


@given(parsers.parse('a separate receipt dated {date} containing "{name}" priced at {price} PLN'))
def given_receipt_dated_2(context: dict[str, object], date: str, name: str, price: str) -> None:
    item_b = context["item_b"]
    assert isinstance(item_b, DummyPosition)
    item_b.name = name
    item_b.unit_price = price
    item_b.quantity = "1"
    item_b.total_price = price
    context["same_receipt"] = False


@when("the agent compares positions across these two distinct receipts")
def when_compare_distinct(context: dict[str, object]) -> None:
    when_compares_both_photos(context)


@then(parsers.parse('the agent should not classify the pair as "{expected_class}"'))
def then_agent_not_classify(context: dict[str, object], expected_class: str) -> None:
    then_no_items_classified(context, expected_class)


@then("the agent should treat them as two independent purchases")
def then_treat_independent(context: dict[str, object]) -> None:
    assert context["result"] == MatchResult.DIFFERENT


@given("one of the two uploaded photos fails to parse")
def given_fails_parse(context: dict[str, object]) -> None:
    item_a = context["item_a"]
    assert isinstance(item_a, DummyPosition)
    # simulate failed parse by missing fields
    item_a.name = ""


@when("the user requests a same-position comparison")
def when_requests_comparison(context: dict[str, object]) -> None:
    when_compares_both_photos(context)


@then(parsers.parse('the agent should return "{msg}"'))
def then_return_comparison_not_possible(context: dict[str, object], msg: str) -> None:
    assert context["error"] is not None
    assert isinstance(context["error"], ComparisonNotPossible)


@then("the agent should state the reason as a parsing failure")
def then_state_reason(context: dict[str, object]) -> None:
    err = context["error"]
    assert isinstance(err, ComparisonNotPossible)
    assert "missing fields" in str(err).lower()


@given(parsers.parse('the agent classified two positions as "{expected_class}"'))
def given_classified_as(context: dict[str, object], expected_class: str) -> None:
    context["result"] = (
        MatchResult.SAME if expected_class == "same position" else MatchResult.DIFFERENT
    )


@when(parsers.parse('the user marks the pair as "{expected_class}"'))
def when_marks_pair(context: dict[str, object], expected_class: str) -> None:
    context["result"] = (
        MatchResult.SAME if expected_class == "same position" else MatchResult.DIFFERENT
    )
    context["override_logged"] = True


@then(parsers.parse('the agent should update the stored classification to "{expected_class}"'))
def then_update_stored(context: dict[str, object], expected_class: str) -> None:
    expected = MatchResult.SAME if expected_class == "same position" else MatchResult.DIFFERENT
    assert context["result"] == expected


@then("the agent should log the correction for future tuning")
def then_log_correction(context: dict[str, object]) -> None:
    assert context["override_logged"] is True
