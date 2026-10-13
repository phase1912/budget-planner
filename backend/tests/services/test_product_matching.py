"""One product across receipts: matching, merging and splitting (F16.1, N2)."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import NotFoundError
from app.models.line_item import LineItem
from app.models.receipt import Receipt, ReceiptStatus
from app.ports.product_matching import MatchQuestion
from app.services.product import ProductService, ProductSummary
from tests.factories.user import UserFactory


class StubMatcher:
    """Answers every question with `answer` and records what it was asked."""

    def __init__(self, answer: str | None) -> None:
        self.answer = answer
        self.asked: list[MatchQuestion] = []

    async def match(self, questions: list[MatchQuestion]) -> dict[str, str | None]:
        self.asked.extend(questions)
        return {q.name: self.answer for q in questions}


async def _receipt(
    session: AsyncSession, user_id: uuid.UUID, shop: str, *lines: tuple[str, str]
) -> Receipt:
    receipt = Receipt(
        id=uuid.uuid4(),
        user_id=user_id,
        merchant_name=shop,
        total_amount=sum((Decimal(p) for _, p in lines), Decimal(0)),
        status=ReceiptStatus.PARSED,
        file_ids=[],
        line_items=[
            LineItem(
                id=uuid.uuid4(),
                name=name,
                quantity=Decimal(1),
                unit_price=Decimal(price),
                total_price=Decimal(price),
            )
            for name, price in lines
        ],
    )
    session.add(receipt)
    await session.flush()
    return receipt


def _by_name(products: list[ProductSummary]) -> dict[str, ProductSummary]:
    return {p.name: p for p in products}


@pytest.mark.asyncio
async def test_one_product_printed_two_ways_in_two_shops_is_one_product(
    db_session: AsyncSession,
) -> None:
    """The demo: "Jogurt Natural 330ml" and "JOG NAT 330ML" are one yoghurt."""
    user = await UserFactory.create_async()
    await _receipt(db_session, user.id, "Biedronka", ("Jogurt Natural 330ml", "4.99"))
    await _receipt(db_session, user.id, "Lidl", ("JOG NAT 330ML", "4.49"))
    await _receipt(db_session, user.id, "Lidl", ("Jogurt natural 330 ml", "4.49"))

    products = await ProductService(db_session).list_products(user.id)

    assert len(products) == 1
    yoghurt = products[0]
    assert (yoghurt.name, yoghurt.purchases, yoghurt.shops) == ("Jogurt Natural 330ml", 3, 2)
    assert (yoghurt.size_amount, yoghurt.size_unit) == (Decimal(330), "ml")
    assert yoghurt.spent == Decimal("13.97")
    assert sorted(v.purchases for v in yoghurt.variants) == [1, 2]


@pytest.mark.asyncio
async def test_discounts_and_zero_lines_are_not_products(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    await _receipt(
        db_session, user.id, "Biedronka", ("Chleb 300g", "4.00"), ("Rabat", "-1.00"), ("Torba", "0")
    )

    products = await ProductService(db_session).list_products(user.id)

    assert [p.name for p in products] == ["Chleb 300g"]


@pytest.mark.asyncio
async def test_an_alike_name_goes_to_the_model_and_joins_the_product_it_names(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    await _receipt(db_session, user.id, "Biedronka", ("Jajko Niespodzianka 20g", "4.99"))
    await ProductService(db_session).list_products(user.id)
    await _receipt(db_session, user.id, "Lidl", ("JajkoNiesMeltie20g", "4.99"))
    matcher = StubMatcher("1")

    products = await ProductService(db_session, matcher).list_products(user.id)

    assert [q.name for q in matcher.asked] == ["JajkoNiesMeltie20g"]
    assert [(p.name, p.purchases) for p in products] == [("Jajko Niespodzianka 20g", 2)]


@pytest.mark.asyncio
async def test_with_no_answer_an_alike_name_is_a_product_of_its_own(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    await _receipt(db_session, user.id, "Biedronka", ("Jajko Niespodzianka 20g", "4.99"))
    await ProductService(db_session).list_products(user.id)
    await _receipt(db_session, user.id, "Lidl", ("JajkoNiesMeltie20g", "4.99"))

    products = await ProductService(db_session, StubMatcher(None)).list_products(user.id)

    assert len(products) == 2


@pytest.mark.asyncio
async def test_merging_moves_lines_and_later_receipts_follow(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    await _receipt(db_session, user.id, "Biedronka", ("Jajko Niespodzianka 20g", "4.99"))
    await _receipt(db_session, user.id, "Lidl", ("Kinder Joy 20g", "5.49"))
    service = ProductService(db_session)
    names = _by_name(await service.list_products(user.id))

    await service.merge(user.id, names["Jajko Niespodzianka 20g"].id, [names["Kinder Joy 20g"].id])
    await _receipt(db_session, user.id, "Lidl", ("KINDER JOY 20G", "5.49"))
    products = await service.list_products(user.id)

    assert [(p.name, p.purchases, p.shops) for p in products] == [("Jajko Niespodzianka 20g", 3, 2)]


@pytest.mark.asyncio
async def test_splitting_takes_a_variant_and_its_lines_into_its_own_product(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    await _receipt(db_session, user.id, "Biedronka", ("Jajko Niespodzianka 20g", "4.99"))
    await _receipt(db_session, user.id, "Lidl", ("Kinder Joy 20g", "5.49"))
    service = ProductService(db_session)
    names = _by_name(await service.list_products(user.id))
    target = names["Jajko Niespodzianka 20g"]
    await service.merge(user.id, target.id, [names["Kinder Joy 20g"].id])
    merged = _by_name(await service.list_products(user.id))["Jajko Niespodzianka 20g"]
    joy = next(v for v in merged.variants if v.printed_name == "Kinder Joy 20g")

    await service.split(user.id, target.id, joy.alias_id)
    await _receipt(db_session, user.id, "Lidl", ("Kinder Joy 20g", "5.49"))
    products = _by_name(await service.list_products(user.id))

    assert (
        products["Jajko Niespodzianka 20g"].purchases,
        products["Kinder Joy 20g"].purchases,
    ) == (
        1,
        2,
    )


@pytest.mark.asyncio
async def test_a_product_printed_one_way_cannot_be_split(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    await _receipt(db_session, user.id, "Biedronka", ("Chleb 300g", "4.00"))
    service = ProductService(db_session)
    bread = (await service.list_products(user.id))[0]

    with pytest.raises(ValueError, match="cannot be split"):
        await service.split(user.id, bread.id, bread.variants[0].alias_id)


@pytest.mark.asyncio
async def test_another_users_purchases_are_never_matched_or_merged(
    db_session: AsyncSession,
) -> None:
    """N2: products, their lines and merges stay within one user."""
    owner, other = await UserFactory.create_async(), await UserFactory.create_async()
    await _receipt(db_session, owner.id, "Biedronka", ("Chleb 300g", "4.00"))
    await _receipt(db_session, other.id, "Biedronka", ("Chleb 300g", "4.00"))
    service = ProductService(db_session)
    mine = await service.list_products(owner.id)
    theirs = await service.list_products(other.id)

    assert [p.purchases for p in mine] == [1]
    assert [p.purchases for p in theirs] == [1]
    assert mine[0].id != theirs[0].id
    with pytest.raises(NotFoundError):
        await service.merge(owner.id, mine[0].id, [theirs[0].id])
    with pytest.raises(NotFoundError):
        await service.split(other.id, mine[0].id, mine[0].variants[0].alias_id)


@pytest.mark.asyncio
async def test_search_finds_a_product_by_any_way_it_is_printed(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    await _receipt(db_session, user.id, "Biedronka", ("Jogurt Natural 330ml", "4.99"))
    await _receipt(db_session, user.id, "Lidl", ("JOG NAT 330ML", "4.49"), ("Chleb 300g", "4.0"))
    service = ProductService(db_session)

    assert [p.name for p in await service.list_products(user.id, "jog nat")] == [
        "Jogurt Natural 330ml"
    ]
    assert [p.name for p in await service.list_products(user.id, "CHLEB")] == ["Chleb 300g"]
