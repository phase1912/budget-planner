"""The month figure over HTTP, against a real database (F6.1, BRD D1, D2, N2)."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.context import current_user_id
from app.db.session import get_db_session
from app.main import create_app
from app.models.line_item import LineItem
from app.models.receipt import Receipt, ReceiptStatus
from app.models.user import User
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory


async def _receipt(
    session: AsyncSession,
    owner: User,
    bought: datetime,
    lines: list[str],
    *,
    status: ReceiptStatus = ReceiptStatus.PARSED,
    uploaded: datetime | None = None,
    printed_total: str | None = None,
) -> Receipt:
    receipt = await ReceiptFactory.create_async(
        user_id=owner.id,
        transaction_date=bought,
        status=status,
        total_amount=Decimal(printed_total) if printed_total else None,
        file_ids=[],
    )
    if uploaded is not None:
        receipt.created_at = uploaded
    await session.refresh(receipt, ["line_items"])
    receipt.line_items = [
        LineItem(
            name=f"Line {i}",
            quantity=Decimal(1),
            unit_price=Decimal(amount),
            total_price=Decimal(amount),
        )
        for i, amount in enumerate(lines)
    ]
    await session.flush()
    return receipt


async def _month(session: AsyncSession, user: User, year: int, month: int) -> Any:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = override_get_db
    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    current_user_id.set(user.id)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        response = await client.get(f"/api/v1/budget/months/{year}/{month}")
    return response


@pytest.mark.asyncio
async def test_the_month_total_is_the_sum_of_its_line_items(db_session: AsyncSession) -> None:
    """D1: line items are summed, not the printed totals, which can be misread."""
    user = await UserFactory.create_async()
    await _receipt(
        db_session, user, datetime(2026, 9, 3, tzinfo=UTC), ["7.00", "30.00"], printed_total="99"
    )
    await _receipt(db_session, user, datetime(2026, 9, 14, tzinfo=UTC), ["12.49"])

    response = await _month(db_session, user, 2026, 9)

    assert response.status_code == 200, response.json()
    body = response.json()
    assert Decimal(body["total"]) == Decimal("49.49")
    assert (body["year"], body["month"], body["receipt_count"]) == (2026, 9, 2)


@pytest.mark.asyncio
async def test_a_back_dated_upload_lands_in_the_month_it_was_bought(
    db_session: AsyncSession,
) -> None:
    """D2: uploaded in September, bought in August, so it is August's spend."""
    user = await UserFactory.create_async()
    await _receipt(
        db_session,
        user,
        datetime(2026, 8, 28, tzinfo=UTC),
        ["20.00"],
        uploaded=datetime(2026, 9, 2, tzinfo=UTC),
    )

    august = (await _month(db_session, user, 2026, 8)).json()
    september = (await _month(db_session, user, 2026, 9)).json()

    assert Decimal(august["total"]) == Decimal("20.00")
    assert Decimal(september["total"]) == Decimal("0")


@pytest.mark.asyncio
async def test_the_last_minute_of_a_month_stays_in_it_and_the_first_of_the_next_does_not(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    await _receipt(db_session, user, datetime(2026, 9, 30, 23, 59, tzinfo=UTC), ["1.00"])
    await _receipt(db_session, user, datetime(2026, 10, 1, 0, 0, tzinfo=UTC), ["2.00"])

    september = (await _month(db_session, user, 2026, 9)).json()
    october = (await _month(db_session, user, 2026, 10)).json()

    assert Decimal(september["total"]) == Decimal("1.00")
    assert Decimal(october["total"]) == Decimal("2.00")


@pytest.mark.asyncio
async def test_a_receipt_under_manual_review_is_held_out_of_the_total(
    db_session: AsyncSession,
) -> None:
    """Domain model invariant 4: only parsed receipts count; F6.2 will report the rest."""
    user = await UserFactory.create_async()
    await _receipt(db_session, user, datetime(2026, 9, 3, tzinfo=UTC), ["10.00"])
    await _receipt(
        db_session,
        user,
        datetime(2026, 9, 4, tzinfo=UTC),
        ["500.00"],
        status=ReceiptStatus.MANUAL_REVIEW,
    )

    body = (await _month(db_session, user, 2026, 9)).json()

    assert (Decimal(body["total"]), body["receipt_count"]) == (Decimal("10.00"), 1)


@pytest.mark.asyncio
async def test_an_empty_month_reads_zero_and_a_new_user_reads_as_having_no_receipts(
    db_session: AsyncSession,
) -> None:
    newcomer = await UserFactory.create_async()
    regular = await UserFactory.create_async()
    await _receipt(db_session, regular, datetime(2026, 7, 5, tzinfo=UTC), ["3.00"])

    fresh = (await _month(db_session, newcomer, 2026, 9)).json()
    quiet = (await _month(db_session, regular, 2026, 9)).json()

    assert (Decimal(fresh["total"]), fresh["has_receipts"]) == (Decimal("0"), False)
    assert (Decimal(quiet["total"]), quiet["has_receipts"]) == (Decimal("0"), True)


@pytest.mark.asyncio
async def test_another_users_receipts_never_count_toward_my_month(
    db_session: AsyncSession,
) -> None:
    """BRD N2."""
    me, someone_else = await UserFactory.create_async(), await UserFactory.create_async()
    await _receipt(db_session, someone_else, datetime(2026, 9, 3, tzinfo=UTC), ["80.00"])

    body = (await _month(db_session, me, 2026, 9)).json()

    assert (Decimal(body["total"]), body["receipt_count"], body["has_receipts"]) == (
        Decimal("0"),
        0,
        False,
    )


@pytest.mark.asyncio
async def test_a_month_that_does_not_exist_is_refused(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    assert (await _month(db_session, user, 2026, 13)).status_code == 422


@pytest.mark.asyncio
async def test_receipts_under_review_are_named_with_their_value_not_quietly_dropped(
    db_session: AsyncSession,
) -> None:
    """D3: the total leaves them out, and the summary says how many and how much."""
    user = await UserFactory.create_async()
    await _receipt(db_session, user, datetime(2026, 9, 3, tzinfo=UTC), ["10.00"])
    for day, lines in ((5, ["60.00", "36.40"]), (9, ["0.00"])):
        await _receipt(
            db_session,
            user,
            datetime(2026, 9, day, tzinfo=UTC),
            lines,
            status=ReceiptStatus.MANUAL_REVIEW,
        )

    body = (await _month(db_session, user, 2026, 9)).json()

    assert Decimal(body["total"]) == Decimal("10.00")
    assert (body["excluded_count"], Decimal(body["excluded_amount"])) == (2, Decimal("96.40"))


@pytest.mark.asyncio
async def test_a_receipt_whose_date_could_not_be_read_is_reported_in_its_upload_month(
    db_session: AsyncSession,
) -> None:
    """With no date it belongs to no month; placed by upload, it is never lost from view."""
    user = await UserFactory.create_async()
    receipt = await ReceiptFactory.create_async(
        user_id=user.id,
        transaction_date=None,
        status=ReceiptStatus.MANUAL_REVIEW,
        file_ids=[],
    )
    receipt.created_at = datetime(2026, 9, 12, tzinfo=UTC)
    await db_session.flush()

    september = (await _month(db_session, user, 2026, 9)).json()
    august = (await _month(db_session, user, 2026, 8)).json()

    assert september["excluded_count"] == 1
    assert august["excluded_count"] == 0
    assert september["has_receipts"] is True


@pytest.mark.asyncio
async def test_another_users_receipts_under_review_are_not_mine_to_resolve(
    db_session: AsyncSession,
) -> None:
    me, someone_else = await UserFactory.create_async(), await UserFactory.create_async()
    await _receipt(
        db_session,
        someone_else,
        datetime(2026, 9, 3, tzinfo=UTC),
        ["80.00"],
        status=ReceiptStatus.MANUAL_REVIEW,
    )

    body = (await _month(db_session, me, 2026, 9)).json()

    assert (body["excluded_count"], Decimal(body["excluded_amount"])) == (0, Decimal("0"))
