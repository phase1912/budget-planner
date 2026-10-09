"""A household reads its members' receipts, never writes them (F12.4, ADR-0017, BRD N2)."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import Receipt, ReceiptStatus
from app.models.user import User
from tests.api.test_household import _call, _household_of
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory


async def _receipt(owner: User, merchant: str, *, private: bool = False) -> Receipt:
    return await ReceiptFactory.create_async(
        user_id=owner.id,
        merchant_name=merchant,
        transaction_date=datetime(2026, 10, 1, tzinfo=UTC),
        total_amount=Decimal("10.00"),
        status=ReceiptStatus.PARSED,
        file_ids=[],
        is_private=private,
    )


def _merchants(response_json: dict[str, list[dict[str, str]]]) -> list[str]:
    return sorted(r["merchant_name"] for r in response_json["items"])


@pytest.mark.asyncio
async def test_the_household_view_lists_every_members_receipts_with_their_owner(
    db_session: AsyncSession,
) -> None:
    me, anna = await UserFactory.create_async(), await UserFactory.create_async()
    await _household_of(me, anna)
    await _receipt(me, "Biedronka")
    await _receipt(anna, "Rossmann")

    response = await _call(db_session, me, "GET", "/receipts?scope=household")

    assert response.status_code == 200, response.json()
    assert _merchants(response.json()) == ["Biedronka", "Rossmann"]
    owners = {r["merchant_name"]: r["user_id"] for r in response.json()["items"]}
    assert owners == {"Biedronka": str(me.id), "Rossmann": str(anna.id)}


@pytest.mark.asyncio
async def test_my_own_view_stays_mine(db_session: AsyncSession) -> None:
    me, anna = await UserFactory.create_async(), await UserFactory.create_async()
    await _household_of(me, anna)
    await _receipt(me, "Biedronka")
    await _receipt(anna, "Rossmann")

    response = await _call(db_session, me, "GET", "/receipts")

    assert _merchants(response.json()) == ["Biedronka"]


@pytest.mark.asyncio
async def test_another_members_private_receipt_is_not_listed(db_session: AsyncSession) -> None:
    me, anna = await UserFactory.create_async(), await UserFactory.create_async()
    await _household_of(me, anna)
    await _receipt(anna, "Rossmann")
    await _receipt(anna, "Pharmacy", private=True)
    await _receipt(me, "My secret", private=True)

    mine = await _call(db_session, me, "GET", "/receipts?scope=household")
    hers = await _call(db_session, anna, "GET", "/receipts?scope=household")

    assert _merchants(mine.json()) == ["My secret", "Rossmann"]
    assert _merchants(hers.json()) == ["Pharmacy", "Rossmann"]


@pytest.mark.asyncio
async def test_a_member_opens_another_members_receipt(db_session: AsyncSession) -> None:
    me, anna = await UserFactory.create_async(), await UserFactory.create_async()
    await _household_of(me, anna)
    hers = await _receipt(anna, "Rossmann")

    response = await _call(db_session, me, "GET", f"/receipts/{hers.id}")

    assert response.status_code == 200
    assert (response.json()["merchant_name"], response.json()["user_id"]) == (
        "Rossmann",
        str(anna.id),
    )


@pytest.mark.asyncio
async def test_another_members_private_receipt_does_not_open(db_session: AsyncSession) -> None:
    me, anna = await UserFactory.create_async(), await UserFactory.create_async()
    await _household_of(me, anna)
    private = await _receipt(anna, "Pharmacy", private=True)

    response = await _call(db_session, me, "GET", f"/receipts/{private.id}")

    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "json"),
    [
        ("DELETE", "", None),
        ("PUT", "/privacy", {"is_private": True}),
        (
            "PATCH",
            "",
            {
                "merchant_name": "Mine now",
                "transaction_date": "2026-10-01",
                "total_amount": "10.00",
                "line_items": [],
            },
        ),
        ("POST", "/keep-duplicate", None),
    ],
)
async def test_another_members_receipt_cannot_be_changed(
    db_session: AsyncSession, method: str, path: str, json: object
) -> None:
    """Membership grants reading only; every write stays the owner's (ADR-0017)."""
    me, anna = await UserFactory.create_async(), await UserFactory.create_async()
    await _household_of(me, anna)
    hers = await _receipt(anna, "Rossmann")

    response = await _call(db_session, me, method, f"/receipts/{hers.id}{path}", json)

    assert response.status_code == 404
    await db_session.refresh(hers)
    assert (hers.merchant_name, hers.is_private) == ("Rossmann", False)


@pytest.mark.asyncio
async def test_a_stranger_reads_nothing_of_a_household(db_session: AsyncSession) -> None:
    me, anna = await UserFactory.create_async(), await UserFactory.create_async()
    stranger = await UserFactory.create_async()
    await _household_of(me, anna)
    hers = await _receipt(anna, "Rossmann")

    listing = await _call(db_session, stranger, "GET", "/receipts?scope=household")
    opened = await _call(db_session, stranger, "GET", f"/receipts/{hers.id}")

    assert (listing.status_code, opened.status_code) == (404, 404)


@pytest.mark.asyncio
async def test_a_removed_member_loses_access_at_once(db_session: AsyncSession) -> None:
    me, anna = await UserFactory.create_async(), await UserFactory.create_async()
    await _household_of(me, anna)
    mine = await _receipt(me, "Biedronka")
    assert (await _call(db_session, anna, "GET", f"/receipts/{mine.id}")).status_code == 200

    await _call(db_session, me, "DELETE", f"/api/v1/household/members/{anna.id}")

    assert (await _call(db_session, anna, "GET", f"/receipts/{mine.id}")).status_code == 404
    listing = await _call(db_session, anna, "GET", "/receipts?scope=household")
    assert listing.status_code == 404


@pytest.mark.asyncio
async def test_the_owner_marks_a_receipt_private_and_back(db_session: AsyncSession) -> None:
    me, anna = await UserFactory.create_async(), await UserFactory.create_async()
    await _household_of(me, anna)
    mine = await _receipt(me, "Pharmacy")

    hidden = await _call(
        db_session, me, "PUT", f"/receipts/{mine.id}/privacy", {"is_private": True}
    )
    while_hidden = await _call(db_session, anna, "GET", f"/receipts/{mine.id}")
    shown = await _call(
        db_session, me, "PUT", f"/receipts/{mine.id}/privacy", {"is_private": False}
    )
    after = await _call(db_session, anna, "GET", f"/receipts/{mine.id}")

    assert (hidden.status_code, hidden.json()["is_private"]) == (200, True)
    assert while_hidden.status_code == 404
    assert (shown.json()["is_private"], after.status_code) == (False, 200)
