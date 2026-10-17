"""Money coming in (F23.10)."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.income import BalanceRead, IncomeRead, IncomeRequest, MonthIncomeRead
from app.services.balance import BalanceService
from app.services.income import IncomeService

router = APIRouter(prefix="/api/v1/income", tags=["income"])

CurrentUser = Annotated[User, Depends(get_current_user)]
Session = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("", response_model=MonthIncomeRead)
async def month_income(
    user: CurrentUser,
    session: Session,
    month: Annotated[str, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")],
) -> MonthIncomeRead:
    """A month's income (YYYY-MM): its entries, or the usual amount standing in."""
    first_day = date.fromisoformat(f"{month}-01")
    view = await IncomeService(session).month(user, first_day)
    return MonthIncomeRead(
        month=month,
        total=view.income.total,
        entered=view.income.entered,
        usual=user.usual_income,
        entries=[IncomeRead.model_validate(e) for e in view.entries],
    )


@router.post("", response_model=IncomeRead, status_code=status.HTTP_201_CREATED)
async def add_income(body: IncomeRequest, _user: CurrentUser, session: Session) -> IncomeRead:
    """Record a sum that came in."""
    return IncomeRead.model_validate(await IncomeService(session).add(body))


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
    )
