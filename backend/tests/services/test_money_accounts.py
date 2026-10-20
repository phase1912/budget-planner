"""Tests for AccountService (F23.15)."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import (
    AuthenticationError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
    ProblemCode,
)
from app.core.context import current_user_id
from app.domain.accounts import AccountKind, MoveKind
from app.models.household import HouseholdRole
from app.models.income_source import IncomeSource
from app.models.regular_expense import RegularExpense
from app.services.money_accounts import AccountService, _me
from tests.factories.household import HouseholdFactory, HouseholdMemberFactory
from tests.factories.user import UserFactory


@pytest.mark.asyncio
async def test_overview_and_history_empty_and_not_found(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    service = AccountService(db_session)

    overview = await service.overview(date(2026, 10, 15))
    assert overview.accounts == []
    assert overview.total == Decimal("0.00")

    with pytest.raises(NotFoundError):
        await service.history(uuid.uuid4(), date(2026, 10, 1), date(2026, 10, 15))

    expected = await service.expected(date(2026, 10, 15))
    assert expected == []


@pytest.mark.asyncio
async def test_create_and_change_accounts_and_purchase_card(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    service = AccountService(db_session)

    # First personal card becomes purchase card automatically
    acc1 = await service.create(
        name="Checking",
        kind=AccountKind.PERSONAL,
        opening=Decimal("100.00"),
        opening_on=date(2026, 10, 1),
        tax_rate=None,
        shared=False,
        for_purchases=False,
    )
    assert acc1.for_purchases is True

    # Second card created with for_purchases=True unmarks the first
    acc2 = await service.create(
        name="Daily Card",
        kind=AccountKind.PERSONAL,
        opening=Decimal("200.00"),
        opening_on=date(2026, 10, 1),
        tax_rate=None,
        shared=False,
        for_purchases=True,
    )
    assert acc2.for_purchases is True
    acc1_reloaded = await service.accounts.get(acc1.id)
    assert acc1_reloaded is not None and not acc1_reloaded.for_purchases

    # Change account
    changed = await service.change(
        acc1.id,
        name="Main Checking",
        opening=Decimal("150.00"),
        opening_on=date(2026, 10, 1),
        tax_rate=None,
        shared=False,
        for_purchases=True,
    )
    assert changed.name == "Main Checking"
    assert changed.for_purchases is True
    acc2_reloaded = await service.accounts.get(acc2.id)
    assert acc2_reloaded is not None and not acc2_reloaded.for_purchases

    # Remove account
    await service.remove(acc2.id)
    with pytest.raises(NotFoundError):
        await service.change(
            acc2.id,
            name="X",
            opening=Decimal(0),
            opening_on=date(2026, 10, 1),
            tax_rate=None,
            shared=False,
            for_purchases=False,
        )


@pytest.mark.asyncio
async def test_money_in_change_income_and_closed_month(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    service = AccountService(db_session)

    biz = await service.create(
        name="Biz",
        kind=AccountKind.BUSINESS,
        opening=Decimal("1000.00"),
        opening_on=date(2026, 10, 1),
        tax_rate=Decimal("10.00"),
        shared=False,
        for_purchases=False,
    )

    today = date(2026, 10, 15)
    inc = await service.money_in(
        biz.id,
        amount=Decimal("500.00"),
        source="Client",
        received_on=date(2026, 10, 5),
        today=today,
    )
    assert inc.amount == Decimal("500.00")
    assert inc.tax == Decimal("50.00")

    # Closed month error on money_in
    with pytest.raises(DomainError) as exc_info:
        await service.money_in(
            biz.id,
            amount=Decimal("100.00"),
            source="Past",
            received_on=date(2026, 9, 30),
            today=today,
        )
    assert exc_info.value.code == ProblemCode.MONTH_CLOSED

    # Change income
    changed = await service.change_income(
        inc.id,
        amount=Decimal("600.00"),
        received_on=date(2026, 10, 6),
        today=today,
    )
    assert changed.amount == Decimal("600.00")
    assert changed.tax == Decimal("60.00")

    # Change income not found
    with pytest.raises(NotFoundError):
        await service.change_income(
            uuid.uuid4(),
            amount=Decimal(10),
            received_on=today,
            today=today,
        )


@pytest.mark.asyncio
async def test_move_adjust_and_moves_crud(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    service = AccountService(db_session)

    a1 = await service.create(
        name="A1",
        kind=AccountKind.PERSONAL,
        opening=Decimal("500.00"),
        opening_on=date(2026, 10, 1),
        tax_rate=None,
        shared=False,
        for_purchases=True,
    )
    a2 = await service.create(
        name="A2",
        kind=AccountKind.PERSONAL,
        opening=Decimal("100.00"),
        opening_on=date(2026, 10, 1),
        tax_rate=None,
        shared=False,
        for_purchases=False,
    )

    today = date(2026, 10, 15)
    # Move to same account
    with pytest.raises(DomainError) as exc_same:
        await service.move(
            from_id=a1.id,
            to_id=a1.id,
            amount=Decimal("50.00"),
            moved_on=today,
            today=today,
        )
    assert exc_same.value.code == ProblemCode.SAME_ACCOUNT

    # Move between accounts
    m = await service.move(
        from_id=a1.id,
        to_id=a2.id,
        amount=Decimal("50.00"),
        moved_on=today,
        today=today,
    )
    assert m.amount == Decimal("50.00")

    # Change move
    ch_m = await service.change_move(m.id, Decimal("70.00"), today, today)
    assert ch_m.amount == Decimal("70.00")

    # Adjust account positive and negative
    adj_pos = await service.adjust(a1.id, Decimal("500.00"), today)
    assert adj_pos.kind == MoveKind.ADJUSTMENT
    adj_neg = await service.adjust(a1.id, Decimal("400.00"), today)
    assert adj_neg.kind == MoveKind.ADJUSTMENT

    # Adjust non-existent
    with pytest.raises(NotFoundError):
        await service.adjust(uuid.uuid4(), Decimal(100), today)

    # Delete move
    await service.delete_move(m.id, today)

    with pytest.raises(NotFoundError):
        await service.delete_move(uuid.uuid4(), today)

    with pytest.raises(NotFoundError):
        await service.change_move(uuid.uuid4(), Decimal(10), today, today)


@pytest.mark.asyncio
async def test_transfer_rules_and_occurrences(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    service = AccountService(db_session)

    a1 = await service.create(
        name="Src",
        kind=AccountKind.PERSONAL,
        opening=Decimal("1000.00"),
        opening_on=date(2026, 10, 1),
        tax_rate=None,
        shared=False,
        for_purchases=True,
    )
    a2 = await service.create(
        name="Dst",
        kind=AccountKind.PERSONAL,
        opening=Decimal("0.00"),
        opening_on=date(2026, 10, 1),
        tax_rate=None,
        shared=False,
        for_purchases=False,
    )

    today = date(2026, 10, 10)
    # Add transfer rule with same accounts
    with pytest.raises(DomainError) as exc_same:
        await service.add_transfer_rule(
            from_id=a1.id,
            to_id=a1.id,
            amount=Decimal("100.00"),
            day=5,
            today=today,
            name=None,
        )
    assert exc_same.value.code == ProblemCode.SAME_ACCOUNT

    rule = await service.add_transfer_rule(
        from_id=a1.id,
        to_id=a2.id,
        amount=Decimal("100.00"),
        day=15,
        today=today,
        name="Savings",
    )
    assert rule.amount == Decimal("100.00")

    # Running transfer rules
    running = await service.transfer_rules()
    assert len(running) == 1

    # Change transfer rule
    ch_rule = await service.change_transfer_rule(
        rule.id,
        amount=Decimal("150.00"),
        day=20,
        name="New Savings",
    )
    assert ch_rule.amount == Decimal("150.00")

    # Transfer rule occurrence change
    occ = await service.set_occurrence("transfer", rule.id, Decimal("180.00"), today)
    assert occ.amount == Decimal("180.00")

    # Occurrence for non-existent rule
    with pytest.raises(NotFoundError):
        await service.set_occurrence("transfer", uuid.uuid4(), Decimal(10), today)

    # End transfer rule
    await service.end_transfer_rule(rule.id, today)
    with pytest.raises(NotFoundError):
        await service.change_transfer_rule(rule.id, amount=Decimal(10), day=1, name="")


@pytest.mark.asyncio
async def test_bill_occurrence_and_confirm_expected(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    service = AccountService(db_session)

    acc = await service.create(
        name="Card",
        kind=AccountKind.PERSONAL,
        opening=Decimal("1000.00"),
        opening_on=date(2026, 10, 1),
        tax_rate=None,
        shared=False,
        for_purchases=True,
    )

    bill = RegularExpense(
        user_id=user.id,
        name="Internet",
        amount=Decimal("50.00"),
        day=5,
        starts_on=date(2026, 10, 1),
        account_id=acc.id,
    )
    db_session.add(bill)
    await db_session.flush()

    today = date(2026, 10, 10)
    occ = await service.set_occurrence("bill", bill.id, Decimal("60.00"), today)
    assert occ.amount == Decimal("60.00")

    # Bill without account_id
    bill_no_acc = RegularExpense(
        user_id=user.id,
        name="No Acc",
        amount=Decimal("30.00"),
        day=5,
        starts_on=date(2026, 10, 1),
        account_id=None,
    )
    db_session.add(bill_no_acc)
    await db_session.flush()

    with pytest.raises(DomainError):
        await service.set_occurrence("bill", bill_no_acc.id, Decimal(40), today)

    # Expected about income and confirm
    source = IncomeSource(
        user_id=user.id,
        name="Client About",
        amount=Decimal("5000.00"),
        day=5,
        starts_on=date(2026, 10, 1),
        about=True,
        account_id=acc.id,
    )
    db_session.add(source)
    await db_session.flush()

    expected_list = await service.expected(today)
    assert len(expected_list) == 1
    assert expected_list[0].amount == Decimal("5000.00")

    confirmed = await service.confirm(source.id, Decimal("5500.00"), today)
    assert confirmed.amount == Decimal("5500.00")

    with pytest.raises(NotFoundError):
        await service.confirm(uuid.uuid4(), Decimal(100), today)


@pytest.mark.asyncio
async def test_household_and_child_rules(db_session: AsyncSession) -> None:
    owner = await UserFactory.create_async(first_name="Owner")
    child = await UserFactory.create_async(first_name="Child")
    household = await HouseholdFactory.create_async()
    await HouseholdMemberFactory.create_async(
        household_id=household.id, user_id=owner.id, role=HouseholdRole.OWNER.value
    )
    await HouseholdMemberFactory.create_async(
        household_id=household.id, user_id=child.id, role=HouseholdRole.CHILD.value
    )

    # Sharing without household
    stranger = await UserFactory.create_async()
    current_user_id.set(stranger.id)
    s_service = AccountService(db_session)
    with pytest.raises(DomainError) as exc_h:
        await s_service.create(
            name="Shared",
            kind=AccountKind.PERSONAL,
            opening=Decimal(0),
            opening_on=date(2026, 10, 1),
            tax_rate=None,
            shared=True,
            for_purchases=False,
        )
    assert exc_h.value.code == ProblemCode.NOT_IN_HOUSEHOLD

    # Owner creates shared account
    current_user_id.set(owner.id)
    o_service = AccountService(db_session)
    shared_acc = await o_service.create(
        name="Family Pot",
        kind=AccountKind.PERSONAL,
        opening=Decimal("500.00"),
        opening_on=date(2026, 10, 1),
        tax_rate=None,
        shared=True,
        for_purchases=True,
    )

    # Child tries to write to shared account -> child_read_only
    current_user_id.set(child.id)
    c_service = AccountService(db_session)
    with pytest.raises(PermissionDeniedError) as exc_c:
        await c_service.change(
            shared_acc.id,
            name="Child Renamed",
            opening=Decimal(0),
            opening_on=date(2026, 10, 1),
            tax_rate=None,
            shared=True,
            for_purchases=False,
        )
    assert exc_c.value.code == ProblemCode.CHILD_READ_ONLY


def test_me_without_context() -> None:
    current_user_id.set(None)
    with pytest.raises(AuthenticationError):
        _me()
