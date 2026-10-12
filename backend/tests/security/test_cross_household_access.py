"""Every endpoint E12 adds or widens, walked as each kind of outsider (F12.6, ADR-0017, N2).

A household grants its members reading and nothing else: a member reads the others'
shared receipts and never changes them, a removed member reads nothing from the next
request on, a stranger never reads anything, and a private receipt's details reach no
one but its owner. One world is built per test and every route is tried against it, so
a later change that opens a route — or a new route that forgets the rule — fails here.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import jwt
import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_storage_service
from app.api.routers.receipts import get_item_categoriser
from app.core.config import get_settings
from app.core.context import current_user_id
from app.db.session import get_db_session
from app.main import create_app
from app.models.category import Category
from app.models.line_item import LineItem
from app.models.receipt import Receipt, ReceiptStatus
from app.models.user import User
from app.ports.storage import receipt_object_name
from app.services.storage import ObjectNotFoundError
from tests.factories.category import CategoryFactory
from tests.factories.household import HouseholdFactory, HouseholdMemberFactory
from tests.factories.line_item import LineItemFactory
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory

SECRETS = ("SecretShop", "SecretItem", "SecretCategory")
"""What only the owner of the private receipt may ever see in a response."""

OCTOBER = "start=2026-10-01&end=2026-10-31"


class RefusingStorage:
    """Holds only the owner's photos; asked for any other object, it has none."""

    def __init__(self, *held: str) -> None:
        self.held = set(held)
        self.asked: list[str] = []

    async def get_object_metadata(self, object_name: str) -> dict[str, str]:
        self.asked.append(object_name)
        if object_name not in self.held:
            raise ObjectNotFoundError(object_name)
        return {}

    async def generate_presigned_url(self, object_name: str, expiration_seconds: int = 3600) -> str:
        return f"https://storage.test/{object_name}"


class UnchangedCategoriser:
    async def categorise_items(self, items: list[Any], categories: Any) -> list[Any]:
        return items


@dataclass
class World:
    """A household of owner and member, a removed ex-member, and a stranger elsewhere."""

    owner: User
    member: User
    removed: User
    stranger: User
    shared: Receipt
    shared_item: LineItem
    private: Receipt
    private_item: LineItem
    members_receipt: Receipt
    removed_receipt: Receipt
    storage: RefusingStorage


async def _receipt(
    user: User, merchant: str, item: str, amount: str, category: Category | None, private: bool
) -> tuple[Receipt, LineItem]:
    receipt = await ReceiptFactory.create_async(
        user_id=user.id,
        merchant_name=merchant,
        transaction_date=datetime(2026, 10, 5, tzinfo=UTC),
        total_amount=Decimal(amount),
        status=ReceiptStatus.PARSED,
        file_ids=[f"{merchant}-photo"],
        is_private=private,
        possible_duplicate_of_id=None,
    )
    line = await LineItemFactory.create_async(
        receipt=receipt,
        name=item,
        quantity=Decimal(1),
        unit_price=Decimal(amount),
        total_price=Decimal(amount),
        category=category,
        position=0,
    )
    return receipt, line


@pytest.fixture
async def world(db_session: AsyncSession) -> World:
    owner = await UserFactory.create_async(first_name="Owner", currency="PLN")
    member = await UserFactory.create_async(first_name="Member", currency="PLN")
    removed = await UserFactory.create_async(first_name="Removed", currency="PLN")
    stranger = await UserFactory.create_async(first_name="Stranger", currency="PLN")
    elsewhere = await UserFactory.create_async(first_name="Elsewhere", currency="PLN")

    home = await HouseholdFactory.create_async(name="Home")
    await HouseholdMemberFactory.create_async(household_id=home.id, user_id=owner.id, role="owner")
    await HouseholdMemberFactory.create_async(household_id=home.id, user_id=member.id)
    removed_membership = await HouseholdMemberFactory.create_async(
        household_id=home.id, user_id=removed.id
    )
    other = await HouseholdFactory.create_async(name="Other")
    await HouseholdMemberFactory.create_async(
        household_id=other.id, user_id=stranger.id, role="owner"
    )
    await HouseholdMemberFactory.create_async(household_id=other.id, user_id=elsewhere.id)

    groceries = await CategoryFactory.create_async(name="Groceries F126", user_id=None)
    secret = await CategoryFactory.create_async(name="SecretCategory", user_id=owner.id)
    shared, shared_item = await _receipt(owner, "SharedShop", "Bread", "10.00", groceries, False)
    private, private_item = await _receipt(owner, "SecretShop", "SecretItem", "90.00", secret, True)
    members_receipt, _ = await _receipt(member, "MembersShop", "Milk", "5.00", groceries, False)
    removed_receipt, _ = await _receipt(removed, "RemovedShop", "Cake", "7.00", groceries, False)

    world = World(
        owner=owner,
        member=member,
        removed=removed,
        stranger=stranger,
        shared=shared,
        shared_item=shared_item,
        private=private,
        private_item=private_item,
        members_receipt=members_receipt,
        removed_receipt=removed_receipt,
        storage=RefusingStorage(
            receipt_object_name(owner.id, "SharedShop-photo"),
            receipt_object_name(owner.id, "SecretShop-photo"),
        ),
    )
    # Removal is the owner's act through the API, as it is in the product.
    response = await _as(
        db_session, world, owner, "DELETE", f"/api/v1/household/members/{removed.id}"
    )
    assert response.status_code == 200, response.json()
    assert removed_membership.id is not None
    return world


async def _as(
    session: AsyncSession, world: World, user: User, method: str, url: str, json: Any = None
) -> Response:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield session

    async def override_storage() -> AsyncIterator[RefusingStorage]:
        yield world.storage

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_storage_service] = override_storage
    app.dependency_overrides[get_item_categoriser] = UnchangedCategoriser
    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    current_user_id.set(user.id)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        return await client.request(method, url, json=json)


def _reads(w: World) -> list[str]:
    """Every read that can now reach another member's receipts, or adds them up."""
    return [
        "/receipts?scope=household",
        "/receipts",
        f"/receipts/{w.shared.id}",
        f"/receipts/{w.private.id}",
        f"/receipts/line-items?{OCTOBER}",
        "/api/v1/household",
        "/api/v1/household/months/2026/10?today=2026-10-20",
        f"/api/v1/household/statistics?{OCTOBER}",
        f"/api/v1/statistics/categories?{OCTOBER}",
        "/api/v1/budget/months/2026/10?today=2026-10-20",
        "/api/v1/budget/months/2026/10/dashboard?today=2026-10-20",
    ]


OUTSIDERS = ["member", "removed", "stranger"]
"""Everyone but the private receipt's owner — the member included, for its details."""


# --- reading -----------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("who", OUTSIDERS)
async def test_a_private_receipts_details_reach_no_one_but_its_owner(
    db_session: AsyncSession, world: World, who: str
) -> None:
    reader: User = getattr(world, who)
    for url in _reads(world):
        response = await _as(db_session, world, reader, "GET", url)
        leaked = [s for s in (*SECRETS, str(world.private.id)) if s in response.text]
        assert leaked == [], f"{who} saw {leaked} at {url}"


@pytest.mark.asyncio
async def test_the_owner_sees_their_private_receipt_so_the_check_above_means_something(
    db_session: AsyncSession, world: World
) -> None:
    response = await _as(db_session, world, world.owner, "GET", f"/receipts/{world.private.id}")

    assert all(s in response.text for s in SECRETS)


@pytest.mark.asyncio
async def test_membership_grants_reading_the_others_shared_receipts(
    db_session: AsyncSession, world: World
) -> None:
    listing = await _as(db_session, world, world.member, "GET", "/receipts?scope=household")
    opened = await _as(db_session, world, world.member, "GET", f"/receipts/{world.shared.id}")

    merchants = sorted(r["merchant_name"] for r in listing.json()["items"])
    assert merchants == ["MembersShop", "SharedShop"]
    assert opened.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("who", ["removed", "stranger"])
async def test_outside_the_household_nothing_of_it_can_be_read(
    db_session: AsyncSession, world: World, who: str
) -> None:
    """The removed member included: removal ends access from the next request (ADR-0017)."""
    reader: User = getattr(world, who)
    for url in (
        f"/receipts/{world.shared.id}",
        f"/receipts/{world.members_receipt.id}",
        f"/receipts/{world.private.id}",
    ):
        assert (await _as(db_session, world, reader, "GET", url)).status_code == 404, url
    listing = await _as(db_session, world, reader, "GET", "/receipts?scope=household")
    if listing.status_code == 200:
        merchants = {r["merchant_name"] for r in listing.json()["items"]}
        assert merchants.isdisjoint({"SharedShop", "MembersShop", "SecretShop"})
    else:
        assert listing.status_code == 404


@pytest.mark.asyncio
async def test_a_removed_members_receipts_leave_the_households_figures(
    db_session: AsyncSession, world: World
) -> None:
    listing = await _as(db_session, world, world.owner, "GET", "/receipts?scope=household")
    month = await _as(
        db_session, world, world.owner, "GET", "/api/v1/household/months/2026/10?today=2026-10-20"
    )

    assert "RemovedShop" not in listing.text
    assert Decimal(month.json()["total"]) == Decimal("105.00")
    assert {m["first_name"] for m in month.json()["members"]} == {"Owner", "Member"}


@pytest.mark.asyncio
async def test_a_strangers_household_figures_hold_none_of_this_households_money(
    db_session: AsyncSession, world: World
) -> None:
    month = await _as(
        db_session,
        world,
        world.stranger,
        "GET",
        "/api/v1/household/months/2026/10?today=2026-10-20",
    )

    assert Decimal(month.json()["total"]) == Decimal("0")


@pytest.mark.asyncio
async def test_a_member_sees_the_photo_of_another_members_shared_receipt(
    db_session: AsyncSession, world: World
) -> None:
    response = await _as(
        db_session, world, world.member, "GET", "/receipts/images/SharedShop-photo"
    )

    assert response.status_code in (302, 307)
    owners_photo = receipt_object_name(world.owner.id, "SharedShop-photo")
    assert response.headers["location"].endswith(owners_photo)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("who", "photo"),
    [
        ("member", "SecretShop-photo"),
        ("removed", "SharedShop-photo"),
        ("removed", "SecretShop-photo"),
        ("stranger", "SharedShop-photo"),
        ("stranger", "SecretShop-photo"),
    ],
)
async def test_a_photo_is_never_signed_for_anyone_who_may_not_read_its_receipt(
    db_session: AsyncSession, world: World, who: str, photo: str
) -> None:
    """A private receipt's photo, and every photo for outsiders, is looked for only under
    the asker's own prefix, where it is not."""
    asker: User = getattr(world, who)

    response = await _as(db_session, world, asker, "GET", f"/receipts/images/{photo}")

    assert response.status_code == 404
    assert world.storage.asked == [receipt_object_name(asker.id, photo)]


# --- writing -----------------------------------------------------------------------


def _writes(receipt: Receipt, item: LineItem) -> list[tuple[str, str, Any]]:
    """Every change that can be made to a receipt or its lines."""
    return [
        (
            "PATCH",
            f"/receipts/{receipt.id}",
            {
                "merchant_name": "Taken over",
                "transaction_date": "2026-10-05",
                "total_amount": "1.00",
                "line_items": [],
            },
        ),
        ("DELETE", f"/receipts/{receipt.id}", None),
        ("PUT", f"/receipts/{receipt.id}/privacy", {"is_private": False}),
        ("PUT", f"/receipts/{receipt.id}/privacy", {"is_private": True}),
        ("POST", f"/receipts/{receipt.id}/keep-duplicate", None),
        ("POST", f"/receipts/{receipt.id}/categorise", None),
        (
            "PATCH",
            f"/receipts/line-items/{item.id}/category",
            {"category_id": None, "apply_to_future": False},
        ),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("which", ["shared", "private"])
@pytest.mark.parametrize("who", ["member", "removed", "stranger"])
async def test_no_one_but_the_owner_changes_a_receipt(
    db_session: AsyncSession, world: World, which: str, who: str
) -> None:
    """Membership grants reading only; every write stays the owner's (ADR-0017)."""
    receipt: Receipt = getattr(world, which)
    item: LineItem = getattr(world, f"{which}_item")
    before = (receipt.merchant_name, receipt.is_private, receipt.total_amount, item.category_id)
    receipt_id, item_id = receipt.id, item.id
    writer: User = getattr(world, who)

    for method, url, body in _writes(receipt, item):
        response = await _as(db_session, world, writer, method, url, body)
        assert response.status_code in (404, 422), f"{who} {method} {url}: {response.status_code}"

    db_session.expire_all()
    stored = await db_session.scalar(select(Receipt).where(Receipt.id == receipt_id))
    line = await db_session.scalar(select(LineItem).where(LineItem.id == item_id))
    assert stored is not None and line is not None
    after = (stored.merchant_name, stored.is_private, stored.total_amount, line.category_id)
    assert after == before


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("PATCH", "", {"name": "Mine now"}),
        ("PUT", "/budget", {"budget_limit": "1.00"}),
        ("POST", "/invite/regenerate", None),
        ("DELETE", "/members/{owner}", None),
    ],
)
async def test_a_member_cannot_manage_the_household(
    db_session: AsyncSession, world: World, method: str, path: str, body: Any
) -> None:
    url = "/api/v1/household" + path.format(owner=world.owner.id)

    response = await _as(db_session, world, world.member, method, url, body)

    assert response.status_code == 403
    household = (await _as(db_session, world, world.owner, "GET", "/api/v1/household")).json()
    assert (household["name"], household["budget_limit"], len(household["members"])) == (
        "Home",
        None,
        2,
    )
