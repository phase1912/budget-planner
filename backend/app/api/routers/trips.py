import uuid
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_exchange_rates
from app.api.routers.receipts import receipt_detail
from app.db.session import get_db_session
from app.domain.per_diem import TripTimes
from app.domain.trips import TripKind, budget_left, settle
from app.models.receipt import Receipt
from app.models.user import User
from app.ports.exchange_rates import ExchangeRatePort
from app.schemas.receipt import ReceiptDetailResponse, ReceiptResponse
from app.schemas.trip import (
    CategoryTotal,
    CurrencyTotal,
    DayTotal,
    ExpenseKindRequest,
    KindTotal,
    PerDiemDayResponse,
    PerDiemPartResponse,
    PerDiemResponse,
    PerDiemTimesRequest,
    PlnRateResponse,
    ReceiptTripRequest,
    SettlementResponse,
    TripDetailResponse,
    TripReceiptResponse,
    TripRequest,
    TripResponse,
    TripSuggestionResponse,
)
from app.services.trip import (
    PerDiem,
    TripDetails,
    TripService,
    TripSummary,
    kind_of,
    story_of,
    trip_spending,
)

router = APIRouter(prefix="/api/v1/trips", tags=["trips"])

CurrentUser = Annotated[User, Depends(get_current_user)]
Rates = Annotated[ExchangeRatePort | None, Depends(get_exchange_rates)]
Session = Annotated[AsyncSession, Depends(get_db_session)]


def trip_response(summary: TripSummary) -> TripResponse:
    """A trip and its totals as the API shows them."""
    trip = summary.trip
    return TripResponse(
        id=trip.id,
        kind=trip.kind,
        name=trip.name,
        country=trip.country,
        city=trip.city,
        start_date=trip.start_date,
        end_date=trip.end_date,
        purpose=trip.purpose,
        receipt_count=summary.receipt_count,
        total=summary.total,
        budget=trip.budget,
        budget_left=budget_left(trip.budget, summary.total),
        advance=trip.advance,
        advance_paid_on=trip.advance_paid_on,
        asking_count=summary.asking_count,
    )


def trip_receipt(receipt: Receipt) -> TripReceiptResponse:
    """A receipt on a trip with its kind; expects its lines and their categories loaded."""
    return TripReceiptResponse(
        **ReceiptResponse.model_validate(receipt).model_dump(),
        expense_kind=kind_of(receipt),
        expense_kind_chosen=receipt.expense_kind_chosen is not None,
    )


def _details(request: TripRequest) -> TripDetails:
    return TripDetails(**request.model_dump())


@router.get("", response_model=list[TripResponse])
async def list_trips(current_user: CurrentUser, session: Session) -> list[TripResponse]:
    """The caller's trips, latest first, each with its receipts' total (F20.1, N2)."""
    return [trip_response(s) for s in await TripService(session).list_trips(current_user.id)]


@router.get("/suggestions", response_model=list[TripSuggestionResponse])
async def trip_suggestions(
    current_user: CurrentUser, session: Session
) -> list[TripSuggestionResponse]:
    """Runs of foreign receipts outside any trip that look like an unrecorded one (F20.1)."""
    return [
        TripSuggestionResponse(**asdict(s))
        for s in await TripService(session).suggestions(current_user.id)
    ]


@router.post("", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def createtrip_response(
    request: TripRequest, current_user: CurrentUser, session: Session
) -> TripResponse:
    """Record a trip; receipts dated within it join it (F20.1).

    Dates meeting another of the caller's trips are refused (409, `trips_overlap`).
    """
    service = TripService(session)
    trip = await service.save(current_user.id, _details(request))
    await session.commit()
    summary, *_ = await service.get(current_user.id, trip.id)
    return trip_response(summary)


@router.get("/{trip_id}", response_model=TripDetailResponse)
async def gettrip_response(
    trip_id: uuid.UUID, current_user: CurrentUser, session: Session, rates: Rates
) -> TripDetailResponse:
    """One trip with its receipts, its spending by kind and currency, and for a business
    trip its per diem (F20.1, F20.2, F20.4). Another user's is not found (N2).
    """
    service = TripService(session)
    summary, receipts, asking = await service.get(current_user.id, trip_id)
    per_diem = await service.per_diem_of(summary.trip, rates, current_user.currency)
    spending = trip_spending(receipts, current_user.currency)
    story = story_of(summary.trip, receipts)
    return TripDetailResponse(
        **trip_response(summary).model_dump(),
        receipts=[trip_receipt(r) for r in receipts],
        asking=[trip_receipt(r) for r in asking],
        days=[DayTotal(day=d, total=t) for d, t in story.days],
        categories=[CategoryTotal(category=c, total=t) for c, t in story.categories],
        by_kind=[KindTotal(kind=k, total=t) for k, t in spending.by_kind.items()],
        by_currency=[
            CurrencyTotal(currency=c, total=t)
            for c, t in sorted(spending.by_currency.items(), key=lambda pair: -pair[1])
        ],
        per_diem=per_diem_response(per_diem),
        settlement=settlement_response(summary, per_diem, current_user.currency),
    )


@router.put("/{trip_id}", response_model=TripResponse)
async def updatetrip_response(
    trip_id: uuid.UUID, request: TripRequest, current_user: CurrentUser, session: Session
) -> TripResponse:
    """Change a trip; its receipts follow its new dates (F20.1). Another's is 404 (N2)."""
    service = TripService(session)
    await service.save(current_user.id, _details(request), trip_id)
    await session.commit()
    summary, *_ = await service.get(current_user.id, trip_id)
    return trip_response(summary)


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletetrip_response(
    trip_id: uuid.UUID, current_user: CurrentUser, session: Session
) -> Response:
    """Forget a trip; its receipts count as they did before it (F20.1). Another's is 404."""
    await TripService(session).delete(current_user.id, trip_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/receipts/{receipt_id}", response_model=ReceiptDetailResponse)
async def place_receipt(
    receipt_id: uuid.UUID, request: ReceiptTripRequest, current_user: CurrentUser, session: Session
) -> ReceiptDetailResponse:
    """Put a receipt in a trip by hand, take it out of any, or give it back to its dates.

    Another user's receipt or trip is not found (N2).
    """
    receipt = await TripService(session).place_receipt(
        receipt_id, request.trip_id, request.automatic
    )
    await session.commit()
    return await receipt_detail(session, receipt, current_user)


@router.put("/receipts/{receipt_id}/kind", response_model=TripReceiptResponse)
async def choose_expense_kind(
    receipt_id: uuid.UUID, request: ExpenseKindRequest, current_user: CurrentUser, session: Session
) -> TripReceiptResponse:
    """Say what a receipt paid for, or (null) give it back to the guess (F20.2).

    Another user's receipt is not found (N2).
    """
    receipt = await TripService(session).choose_kind(receipt_id, request.kind)
    await session.commit()
    return trip_receipt(receipt)


def per_diem_response(per_diem: PerDiem | None) -> PerDiemResponse | None:
    """A business trip's per diem as the API shows it, or None without one."""
    if per_diem is None:
        return None
    times = per_diem.times
    return PerDiemResponse(
        departure=times.departure,
        returned=times.returned,
        abroad_from=times.abroad_from,
        abroad_to=times.abroad_to,
        meals=[list(day) for day in times.meals],
        parts=[
            PerDiemPartResponse(
                abroad=part.abroad,
                country=part.country,
                currency=part.rate.currency,
                rate=part.rate.amount,
                days=[
                    PerDiemDayResponse(**{**asdict(day), "meals": list(day.meals)})
                    for day in part.days
                ],
                total=part.total,
            )
            for part in per_diem.parts
        ],
        to_pln=[
            PlnRateResponse(
                currency=currency,
                rate=rate.rate if rate else None,
                effective_date=rate.effective_date if rate else None,
                source=rate.source if rate else None,
            )
            for currency, rate in sorted(per_diem.to_pln.items())
        ],
        total_pln=per_diem.total_pln,
        account_currency=per_diem.account_currency,
        total_account=per_diem.total_account,
    )


def settlement_response(
    summary: TripSummary, per_diem: PerDiem | None, currency: str
) -> SettlementResponse | None:
    """A business trip's sum to hand in, as the API shows it; None for a personal trip."""
    trip = summary.trip
    if trip.kind is not TripKind.BUSINESS:
        return None
    sums = settle(
        summary.total,
        per_diem is not None,
        per_diem.total_account if per_diem else None,
        trip.advance,
    )
    return SettlementResponse(currency=currency, **asdict(sums))


@router.put("/{trip_id}/per-diem", response_model=PerDiemResponse)
async def set_per_diem_times(
    trip_id: uuid.UUID,
    request: PerDiemTimesRequest,
    current_user: CurrentUser,
    session: Session,
    rates: Rates,
) -> PerDiemResponse | None:
    """Give a business trip's times and meals; its per diem comes back itemised (F20.4).

    A personal trip, times out of order, or a trip before the rates kept is 422; another
    user's trip is 404 (N2).
    """
    service = TripService(session)
    times = TripTimes(
        departure=request.departure,
        returned=request.returned,
        abroad_from=request.abroad_from,
        abroad_to=request.abroad_to,
        meals=tuple(tuple(day) for day in request.meals),
    )
    trip = await service.set_times(current_user.id, trip_id, times)
    await session.commit()
    return per_diem_response(await service.per_diem_of(trip, rates, current_user.currency))


@router.delete("/{trip_id}/per-diem", status_code=status.HTTP_204_NO_CONTENT)
async def clear_per_diem_times(
    trip_id: uuid.UUID, current_user: CurrentUser, session: Session
) -> Response:
    """Forget a business trip's times: it has no per diem until given again (F20.4)."""
    await TripService(session).set_times(current_user.id, trip_id, None)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
