"""Where the money is: accounts, their histories and the money between them (F23.15)."""

import uuid
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.domain.accounts import is_closed
from app.models.income import Income
from app.models.user import User
from app.schemas.income import IncomeRead
from app.schemas.money_accounts import (
    AccountRead,
    AccountRequest,
    AccountsRead,
    AdjustRequest,
    ConfirmRequest,
    EntryRead,
    ExpectedRead,
    HistoryRead,
    IncomeChange,
    MoneyInRequest,
    MoveChange,
    MoveRequest,
    OccurrenceRequest,
    TransferRuleRead,
    TransferRuleRequest,
)
from app.services.money_accounts import AccountService, AccountView

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])

CurrentUser = Annotated[User, Depends(get_current_user)]
Session = Annotated[AsyncSession, Depends(get_db_session)]
Today = Annotated[date | None, Query(description="The caller's own date")]


def _today(today: date | None) -> date:
    return today or datetime.now(UTC).date()


def _account(view: AccountView) -> AccountRead:
    """An account as the caller sees it, with what is on it now."""
    account = view.account
    return AccountRead(
        id=account.id,
        name=account.name,
        kind=account.kind,
        opening=account.opening,
        opening_on=account.opening_on,
        tax_rate=account.tax_rate,
        for_purchases=account.for_purchases,
        balance=view.ledger.balance,
        set_aside=view.ledger.set_aside,
        shared=account.household_id is not None,
        mine=view.mine,
        added_by=view.added_by,
    )


async def _read_one(service: AccountService, account_id: uuid.UUID, today: date) -> AccountRead:
    view, _ = await service.history(account_id, today.replace(day=1), today)
    return _account(view)


@router.get("", response_model=AccountsRead)
async def list_accounts(_user: CurrentUser, session: Session, today: Today = None) -> AccountsRead:
    """Every account the caller sees — their own and the household's — with balances."""
    overview = await AccountService(session).overview(_today(today))
    return AccountsRead(
        accounts=[_account(a) for a in overview.accounts],
        total=overview.total,
        set_aside=overview.set_aside,
    )


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
async def open_account(
    body: AccountRequest, _user: CurrentUser, session: Session, today: Today = None
) -> AccountRead:
    """Open an account; the first everyday one pays for purchases by itself."""
    service = AccountService(session)
    day = _today(today)
    account = await service.create(
        name=body.name,
        kind=body.kind,
        opening=body.opening,
        opening_on=body.opening_on or day,
        tax_rate=body.tax_rate,
        shared=body.shared,
        for_purchases=body.for_purchases,
    )
    return await _read_one(service, account.id, day)


@router.put("/{account_id}", response_model=AccountRead)
async def change_account(
    account_id: uuid.UUID,
    body: AccountRequest,
    _user: CurrentUser,
    session: Session,
    today: Today = None,
) -> AccountRead:
    """Change an account; 404 unless the caller's or their household's (N2)."""
    service = AccountService(session)
    day = _today(today)
    account = await service.change(
        account_id,
        name=body.name,
        opening=body.opening,
        opening_on=body.opening_on or day,
        tax_rate=body.tax_rate,
        shared=body.shared,
        for_purchases=body.for_purchases,
    )
    return await _read_one(service, account.id, day)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(account_id: uuid.UUID, _user: CurrentUser, session: Session) -> Response:
    """Delete an account and the moves on it; 404 unless the caller sees it (N2)."""
    await AccountService(session).remove(account_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/expected", response_model=list[ExpectedRead])
async def expected_income(
    _user: CurrentUser, session: Session, today: Today = None
) -> list[ExpectedRead]:
    """ "About" incomes whose day has come this month, waiting to be confirmed (F_Check)."""
    entries = await AccountService(session).expected(_today(today))
    return [
        ExpectedRead(
            source_id=e.ref[1], account_id=e.account_id, name=e.name, day=e.day, amount=e.amount
        )
        for e in entries
        if e.ref is not None
    ]


@router.get("/{account_id}/history", response_model=HistoryRead)
async def account_history(
    account_id: uuid.UUID,
    _user: CurrentUser,
    session: Session,
    month: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}$")] = None,
    today: Today = None,
) -> HistoryRead:
    """One account's history in a month, newest first; earlier months are closed."""
    day = _today(today)
    first_day = date.fromisoformat(f"{month}-01") if month else day.replace(day=1)
    view, entries = await AccountService(session).history(account_id, first_day, day)
    closed = is_closed(first_day, day)
    return HistoryRead(
        account=_account(view),
        month=first_day.strftime("%Y-%m"),
        closed=closed,
        entries=[
            EntryRead(
                day=e.day,
                kind=e.kind,
                name=e.name,
                amount=e.amount,
                tax=e.tax,
                by_rule=e.by_rule,
                upcoming=e.upcoming,
                count=e.count,
                author=e.author,
                ref=e.ref[0] if e.ref else None,
                ref_id=e.ref[1] if e.ref else None,
                editable=not closed and e.ref is not None,
            )
            for e in entries
        ],
    )


@router.post("/{account_id}/money-in", status_code=status.HTTP_201_CREATED)
async def money_in(
    account_id: uuid.UUID,
    body: MoneyInRequest,
    _user: CurrentUser,
    session: Session,
    today: Today = None,
) -> Response:
    """Money reached an account: income from outside — taxed on a business account — or a
    transfer from another own account, which is neither income nor spending."""
    service = AccountService(session)
    day = _today(today)
    if body.from_account_id is not None:
        await service.move(
            from_id=body.from_account_id,
            to_id=account_id,
            amount=body.amount,
            moved_on=body.received_on,
            today=day,
        )
    else:
        await service.money_in(
            account_id,
            amount=body.amount,
            source=body.source,
            received_on=body.received_on,
            today=day,
        )
    return Response(status_code=status.HTTP_201_CREATED)


@router.post("/moves", status_code=status.HTTP_201_CREATED)
async def move_money(
    body: MoveRequest, _user: CurrentUser, session: Session, today: Today = None
) -> Response:
    """Move money between two accounts the caller sees (N2)."""
    await AccountService(session).move(
        from_id=body.from_account_id,
        to_id=body.to_account_id,
        amount=body.amount,
        moved_on=body.moved_on,
        today=_today(today),
        name=body.name,
    )
    return Response(status_code=status.HTTP_201_CREATED)


@router.put("/moves/{move_id}", status_code=status.HTTP_204_NO_CONTENT)
async def change_move(
    move_id: uuid.UUID, body: MoveChange, _user: CurrentUser, session: Session, today: Today = None
) -> Response:
    """Correct a move of this month; 409 month_closed for an earlier one."""
    await AccountService(session).change_move(move_id, body.amount, body.moved_on, _today(today))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/moves/{move_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_move(
    move_id: uuid.UUID, _user: CurrentUser, session: Session, today: Today = None
) -> Response:
    """Remove a move of this month; 409 month_closed for an earlier one."""
    await AccountService(session).delete_move(move_id, _today(today))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/incomes/{income_id}", status_code=status.HTTP_204_NO_CONTENT)
async def change_income(
    income_id: uuid.UUID,
    body: IncomeChange,
    _user: CurrentUser,
    session: Session,
    today: Today = None,
) -> Response:
    """Correct an income on an account this month; its tax follows the account's rate."""
    await AccountService(session).change_income(
        income_id, body.amount, body.received_on, _today(today)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{account_id}/adjust", status_code=status.HTTP_201_CREATED)
async def adjust_account(
    account_id: uuid.UUID,
    body: AdjustRequest,
    _user: CurrentUser,
    session: Session,
    today: Today = None,
) -> Response:
    """Bring an account to what the bank says, by a correction of the difference."""
    await AccountService(session).adjust(account_id, body.balance, _today(today))
    return Response(status_code=status.HTTP_201_CREATED)


@router.put("/occurrences/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def change_occurrence(
    rule_id: uuid.UUID,
    body: OccurrenceRequest,
    _user: CurrentUser,
    session: Session,
    today: Today = None,
) -> Response:
    """Change this month's bill or transfer made by a rule; 0 skips it this month."""
    await AccountService(session).set_occurrence(body.kind, rule_id, body.amount, _today(today))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/expected/{source_id}/confirm", response_model=IncomeRead)
async def confirm_expected(
    source_id: uuid.UUID,
    body: ConfirmRequest,
    _user: CurrentUser,
    session: Session,
    today: Today = None,
) -> IncomeRead:
    """Say what an "about" income really brought this month; a bonus counts once."""
    income: Income = await AccountService(session).confirm(source_id, body.amount, _today(today))
    return IncomeRead.model_validate(income).model_copy(
        update={"shared": income.household_id is not None}
    )


@router.get("/transfers", response_model=list[TransferRuleRead])
async def transfer_rules(_user: CurrentUser, session: Session) -> list[TransferRuleRead]:
    """The monthly transfers still running, between accounts the caller sees."""
    return [
        TransferRuleRead.model_validate(r) for r in await AccountService(session).transfer_rules()
    ]


@router.post("/transfers", response_model=TransferRuleRead, status_code=status.HTTP_201_CREATED)
async def add_transfer_rule(
    body: TransferRuleRequest, _user: CurrentUser, session: Session, today: Today = None
) -> TransferRuleRead:
    """Move money every month by itself; a day already past this month starts next month."""
    rule = await AccountService(session).add_transfer_rule(
        from_id=body.from_account_id,
        to_id=body.to_account_id,
        amount=body.amount,
        day=body.day,
        today=_today(today),
        name=body.name,
    )
    return TransferRuleRead.model_validate(rule)


@router.put("/transfers/{rule_id}", response_model=TransferRuleRead)
async def change_transfer_rule(
    rule_id: uuid.UUID, body: TransferRuleRequest, _user: CurrentUser, session: Session
) -> TransferRuleRead:
    """Change a monthly transfer from now on; 404 unless the caller sees it (N2)."""
    rule = await AccountService(session).change_transfer_rule(
        rule_id, amount=body.amount, day=body.day, name=body.name or ""
    )
    return TransferRuleRead.model_validate(rule)


@router.delete("/transfers/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def end_transfer_rule(
    rule_id: uuid.UUID, _user: CurrentUser, session: Session, today: Today = None
) -> Response:
    """Stop a monthly transfer from next month; past months keep it."""
    await AccountService(session).end_transfer_rule(rule_id, _today(today))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
