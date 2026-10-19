"""Money coming in (F23.10)."""

import uuid
from dataclasses import asdict
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.income_document_agent import IncomeDocumentAdapter
from app.agent.factory import agent_from_settings
from app.api import rate_limit
from app.api.dependencies import get_confirmed_user, get_current_user, get_quota_service
from app.api.rate_limit import limiter
from app.db.session import get_db_session
from app.models.income import Income
from app.models.income_source import IncomeSource
from app.models.regular_expense import RegularExpense
from app.models.user import User
from app.ports.income_reading import IncomeReaderPort
from app.schemas.income import (
    BalanceRead,
    IncomeDraft,
    IncomeRead,
    IncomeRequest,
    IncomeSourceRead,
    IncomeSourceRequest,
    MonthIncomeRead,
    PendingIncomeRead,
    RegularExpenseRead,
    RegularExpenseRequest,
    TaxPaymentRead,
    TaxPaymentRequest,
)
from app.services.balance import BalanceService
from app.services.income import IncomeService, Sharing
from app.services.income_document import IncomeDocumentService
from app.services.quota import QuotaService

router = APIRouter(prefix="/api/v1/income", tags=["income"])

CurrentUser = Annotated[User, Depends(get_current_user)]
Session = Annotated[AsyncSession, Depends(get_db_session)]


def _income(row: Income, sharing: Sharing) -> IncomeRead:
    """An entry as the caller sees it: whose it is (F12.8)."""
    return IncomeRead.model_validate(row).model_copy(update=asdict(sharing.whose(row)))


def _regular(row: IncomeSource, sharing: Sharing) -> IncomeSourceRead:
    """A regular income as the caller sees it: whose it is (F12.8)."""
    return IncomeSourceRead.model_validate(row).model_copy(update=asdict(sharing.whose(row)))


def _bill(row: RegularExpense, sharing: Sharing) -> RegularExpenseRead:
    """A regular bill as the caller sees it: whose it is, its split and their part (F12.8)."""
    return RegularExpenseRead.model_validate(row).model_copy(
        update={**asdict(sharing.whose(row)), "split": row.split, "my_part": sharing.part_of(row)}
    )


def _this_month() -> date:
    return datetime.now(UTC).date().replace(day=1)


@router.get("", response_model=MonthIncomeRead)
async def month_income(
    user: CurrentUser,
    session: Session,
    month: Annotated[str, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")],
) -> MonthIncomeRead:
    """A month's income (YYYY-MM): its entries, or the usual amount standing in."""
    first_day = date.fromisoformat(f"{month}-01")
    service = IncomeService(session)
    view = await service.month(user, first_day)
    sharing = await service.sharing(first_day)
    return MonthIncomeRead(
        month=month,
        total=view.income.total,
        entered=view.income.entered,
        usual=user.usual_income,
        entries=[_income(e, sharing) for e in view.entries],
        taxes=view.income.taxes,
        net=view.income.net,
        taxes_paid=view.taxes_paid,
        regular=[_regular(s, sharing) for s in view.regular],
        bills=[_bill(b, sharing) for b in view.bills],
        bills_total=sum((b.amount for b in view.bills), Decimal("0.00")),
    )


@router.post("", response_model=IncomeRead, status_code=status.HTTP_201_CREATED)
async def add_income(body: IncomeRequest, _user: CurrentUser, session: Session) -> IncomeRead:
    """Record a sum that came in; `shared` puts it in the household's money (F12.8)."""
    service = IncomeService(session)
    income = await service.add(body)
    return _income(income, await service.sharing(_this_month()))


def get_income_reader() -> IncomeReaderPort:
    """Provide the income reader port; tests override this to stay off the network."""
    return IncomeDocumentAdapter(agent_from_settings())


@router.post("/read", response_model=IncomeDraft)
@limiter.limit(rate_limit.UPLOAD)
async def read_income_document(
    request: Request,
    file: UploadFile,
    user: Annotated[User, Depends(get_confirmed_user)],
    quota: Annotated[QuotaService, Depends(get_quota_service)],
    reader: Annotated[IncomeReaderPort, Depends(get_income_reader)],
) -> IncomeDraft:
    """Read a payslip or transfer confirmation into an entry to confirm (F23.11).

    Nothing is stored: the file is read in memory and dropped, and only what the user
    then confirms is saved, through `POST /income` with `channel` document. Counts
    against the same reading limits as receipts (F10.6); refuses a document that is not
    about money received (`not_income`) or cannot be read (`income_unreadable`).
    """
    await quota.ensure_can_read(user, 1, datetime.now(UTC))
    reading = await IncomeDocumentService(reader).read(await file.read())
    return IncomeDraft(
        amount=reading.amount,
        received_on=reading.received_on,
        source=reading.source,
        kind=reading.kind,
    )


@router.get("/pending", response_model=list[PendingIncomeRead])
async def pending_income(_user: CurrentUser, session: Session) -> list[PendingIncomeRead]:
    """Income read off forwarded payslips or transfers, waiting to be confirmed (F23.11)."""
    return [PendingIncomeRead.model_validate(p) for p in await IncomeService(session).waiting()]


@router.post(
    "/pending/{pending_id}", response_model=IncomeRead, status_code=status.HTTP_201_CREATED
)
async def confirm_pending_income(
    pending_id: uuid.UUID, body: IncomeRequest, _user: CurrentUser, session: Session
) -> IncomeRead:
    """Confirm a pending income as `body` says, making it an entry; 404 if not the user's."""
    service = IncomeService(session)
    income = await service.confirm(pending_id, body)
    return _income(income, await service.sharing(_this_month()))


@router.delete("/pending/{pending_id}", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_pending_income(
    pending_id: uuid.UUID, _user: CurrentUser, session: Session
) -> Response:
    """Drop a pending income without keeping it; 404 if not the user's (N2)."""
    await IncomeService(session).dismiss(pending_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/regular", response_model=list[IncomeSourceRead])
async def regular_incomes(_user: CurrentUser, session: Session) -> list[IncomeSourceRead]:
    """The regular incomes still running, already net — the caller's and shared (F23.17)."""
    service = IncomeService(session)
    sharing = await service.sharing(_this_month())
    return [_regular(s, sharing) for s in await service.regular_incomes()]


@router.post("/regular", response_model=IncomeSourceRead, status_code=status.HTTP_201_CREATED)
async def add_regular_income(
    body: IncomeSourceRequest,
    _user: CurrentUser,
    session: Session,
    today: Annotated[date | None, Query(description="The caller's own date")] = None,
) -> IncomeSourceRead:
    """Start a regular income; it counts every month from this one on."""
    service = IncomeService(session)
    source = await service.add_regular(body, today or datetime.now(UTC).date())
    return _regular(source, await service.sharing(_this_month()))


@router.put("/regular/{source_id}", response_model=IncomeSourceRead)
async def change_regular_income(
    source_id: uuid.UUID, body: IncomeSourceRequest, _user: CurrentUser, session: Session
) -> IncomeSourceRead:
    """Change a regular income; 404 unless the caller's or their household's (N2, F12.8)."""
    service = IncomeService(session)
    source = await service.change_regular(source_id, body)
    return _regular(source, await service.sharing(_this_month()))


@router.delete("/regular/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def end_regular_income(
    source_id: uuid.UUID,
    _user: CurrentUser,
    session: Session,
    today: Annotated[date | None, Query(description="The caller's own date")] = None,
) -> Response:
    """Stop a regular income from next month; past months keep it. 404 if not the user's."""
    await IncomeService(session).end_regular(source_id, today or datetime.now(UTC).date())
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/bills", response_model=list[RegularExpenseRead])
async def regular_bills(_user: CurrentUser, session: Session) -> list[RegularExpenseRead]:
    """The regular bills still running — the caller's and shared (F23.18, F12.8)."""
    service = IncomeService(session)
    sharing = await service.sharing(_this_month())
    return [_bill(b, sharing) for b in await service.regular_bills()]


@router.post("/bills", response_model=RegularExpenseRead, status_code=status.HTTP_201_CREATED)
async def add_bill(
    body: RegularExpenseRequest,
    _user: CurrentUser,
    session: Session,
    today: Annotated[date | None, Query(description="The caller's own date")] = None,
) -> RegularExpenseRead:
    """Start a regular bill; it counts every month from this one on."""
    service = IncomeService(session)
    bill = await service.add_bill(body, today or datetime.now(UTC).date())
    return _bill(bill, await service.sharing(_this_month()))


@router.put("/bills/{bill_id}", response_model=RegularExpenseRead)
async def change_bill(
    bill_id: uuid.UUID, body: RegularExpenseRequest, _user: CurrentUser, session: Session
) -> RegularExpenseRead:
    """Change a regular bill; 404 unless the caller's or their household's (N2, F12.8)."""
    service = IncomeService(session)
    bill = await service.change_bill(bill_id, body)
    return _bill(bill, await service.sharing(_this_month()))


@router.delete("/bills/{bill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def end_bill(
    bill_id: uuid.UUID,
    _user: CurrentUser,
    session: Session,
    today: Annotated[date | None, Query(description="The caller's own date")] = None,
) -> Response:
    """Stop a regular bill from next month; past months keep it. 404 if not the user's."""
    await IncomeService(session).end_bill(bill_id, today or datetime.now(UTC).date())
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/taxes", response_model=list[TaxPaymentRead])
async def tax_payments(
    _user: CurrentUser,
    session: Session,
    month: Annotated[str, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")],
) -> list[TaxPaymentRead]:
    """A month's tax payments (YYYY-MM), for a user who pays their own (F23.16)."""
    first_day = date.fromisoformat(f"{month}-01")
    return [
        TaxPaymentRead.model_validate(p)
        for p in await IncomeService(session).tax_payments_of(first_day)
    ]


@router.post("/taxes", response_model=TaxPaymentRead, status_code=status.HTTP_201_CREATED)
async def pay_taxes(
    body: TaxPaymentRequest, _user: CurrentUser, session: Session
) -> TaxPaymentRead:
    """Record taxes paid: they leave the balance, never the spending (F23.16)."""
    return TaxPaymentRead.model_validate(await IncomeService(session).pay_taxes(body))


@router.delete("/taxes/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tax_payment(
    payment_id: uuid.UUID, _user: CurrentUser, session: Session
) -> Response:
    """Remove a tax payment; 404 if it is not the user's (N2)."""
    await IncomeService(session).delete_tax_payment(payment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{income_id}", response_model=IncomeRead)
async def update_income(
    income_id: uuid.UUID, body: IncomeRequest, _user: CurrentUser, session: Session
) -> IncomeRead:
    """Change an entry; 404 for one that is not the user's (N2)."""
    return IncomeRead.model_validate(await IncomeService(session).update(income_id, body))


@router.delete("/{income_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_income(income_id: uuid.UUID, _user: CurrentUser, session: Session) -> Response:
    """Remove an entry; 404 for one that is not the user's (N2)."""
    await IncomeService(session).delete(income_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/balance", response_model=BalanceRead)
async def balance(user: CurrentUser, session: Session, today: date) -> BalanceRead:
    """What the user has on `today` (their own date): the start, plus income, minus spend."""
    found = await BalanceService(session).balance_of(user, today)
    if found is None:
        return BalanceRead(balance=None, since=None, starting=None, came_in=None, spent=None)
    return BalanceRead(
        balance=found.now,
        since=found.since,
        starting=found.starting,
        came_in=found.came_in,
        spent=found.spent,
        taxes_paid=found.taxes_paid,
        bills=found.bills,
        for_taxes=found.for_taxes if user.pays_own_taxes else None,
    )
