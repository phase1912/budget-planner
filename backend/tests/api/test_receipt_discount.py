"""A discount the receipt does not print: paid 69 of the 169 printed (F23.7, N2)."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import Receipt, ReceiptStatus
from app.models.user import User
from tests.api.test_income import _call
from tests.factories.category import CategoryFactory
from tests.factories.line_item import LineItemFactory
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory

MONTH = "/api/v1/budget/months/2026/10/dashboard?today=2026-10-20"


async def _receipt(user: User) -> Receipt:
    receipt = await ReceiptFactory.create_async(
        user_id=user.id,
        transaction_date=datetime(2026, 10, 12, tzinfo=UTC),
        total_amount=Decimal("169.00"),
        status=ReceiptStatus.PARSED,
        file_ids=[],
        paid_discount=None,
    )
    groceries = await CategoryFactory.create_async(user_id=None, name="Groceries")
    clothes = await CategoryFactory.create_async(user_id=None, name="Clothes")
    for name, price, category in [("Coffee", "119.00", groceries), ("T-shirt", "50.00", clothes)]:
        await LineItemFactory.create_async(
            receipt=receipt,
            name=name,
            quantity=Decimal(1),
            unit_price=Decimal(price),
            total_price=Decimal(price),
            discount_share=Decimal(0),
            category=category,
        )
    return receipt


@pytest.mark.asyncio
async def test_the_month_counts_what_was_paid_and_the_shelf_price_stays(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    receipt = await _receipt(user)
    url = f"/receipts/{receipt.id}/discount"

    applied = await _call(db_session, "PUT", url, user=user, json={"amount": "100.00"})

    assert applied.status_code == 200
    body = applied.json()
    assert body["paid_discount"] == "100.00"
    shares = {line["name"]: line["discount_share"] for line in body["line_items"]}
    # 70.414… and 29.585… cut to the grosz; the grosz left over goes to the dearest line.
    assert shares == {"Coffee": "70.42", "T-shirt": "29.58"}
    assert {line["unit_price"] for line in body["line_items"]} == {"119.00", "50.00"}
    month = (await _call(db_session, "GET", MONTH, user=user)).json()
    assert month["summary"]["total"] == "69.00"
    by_category = {c["name"]: c["total_amount"] for c in month["categories"]}
    assert by_category == {"Groceries": "48.58", "Clothes": "20.42"}

    removed = await _call(db_session, "PUT", url, user=user, json={"amount": None})
    assert removed.json()["paid_discount"] is None
    assert (await _call(db_session, "GET", MONTH, user=user)).json()["summary"]["total"] == "169.00"


@pytest.mark.asyncio
async def test_a_discount_on_some_lines_only_and_one_too_large(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    receipt = await _receipt(user)
    url = f"/receipts/{receipt.id}/discount"
    lines = (await _call(db_session, "PUT", url, user=user, json={"amount": None})).json()
    shirt_id = next(line["id"] for line in lines["line_items"] if line["name"] == "T-shirt")

    some = await _call(
        db_session, "PUT", url, user=user, json={"amount": "20.00", "line_ids": [shirt_id]}
    )
    shares = {line["name"]: line["discount_share"] for line in some.json()["line_items"]}
    assert shares == {"Coffee": "0.00", "T-shirt": "20.00"}

    too_much = await _call(
        db_session, "PUT", url, user=user, json={"amount": "60.00", "line_ids": [shirt_id]}
    )
    assert too_much.status_code == 409
    assert too_much.json()["code"] == "discount_too_large"


@pytest.mark.asyncio
async def test_another_users_receipt_takes_no_discount(db_session: AsyncSession) -> None:
    owner = await UserFactory.create_async()
    stranger = await UserFactory.create_async()
    receipt = await _receipt(owner)

    refused = await _call(
        db_session,
        "PUT",
        f"/receipts/{receipt.id}/discount",
        user=stranger,
        json={"amount": "10.00"},
    )
    assert refused.status_code == 404
