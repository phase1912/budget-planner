import uuid
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.routers.receipts import receipt_detail
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.receipt import ReceiptDetailResponse, ReceiptResponse
from app.schemas.trip import (
    ReceiptTripRequest,
    TripDetailResponse,
    TripRequest,
    TripResponse,
    TripSuggestionResponse,
)
from app.services.trip import TripDetails, TripService, TripSummary

router = APIRouter(prefix="/api/v1/trips", tags=["trips"])

CurrentUser = Annotated[User, Depends(get_current_user)]
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
    summary, _ = await service.get(current_user.id, trip.id)
    return trip_response(summary)


@router.get("/{trip_id}", response_model=TripDetailResponse)
async def gettrip_response(
    trip_id: uuid.UUID, current_user: CurrentUser, session: Session
) -> TripDetailResponse:
    """One trip with its receipts (F20.1). Another user's is not found (N2)."""
    summary, receipts = await TripService(session).get(current_user.id, trip_id)
    return TripDetailResponse(
        **trip_response(summary).model_dump(),
        receipts=[ReceiptResponse.model_validate(r) for r in receipts],
    )


@router.put("/{trip_id}", response_model=TripResponse)
async def updatetrip_response(
    trip_id: uuid.UUID, request: TripRequest, current_user: CurrentUser, session: Session
) -> TripResponse:
    """Change a trip; its receipts follow its new dates (F20.1). Another's is 404 (N2)."""
    service = TripService(session)
    await service.save(current_user.id, _details(request), trip_id)
    await session.commit()
    summary, _ = await service.get(current_user.id, trip_id)
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
