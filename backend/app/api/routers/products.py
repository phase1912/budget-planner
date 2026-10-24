import uuid
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.product_matching_agent import ProductMatchingAdapter
from app.agent.factory import agent_from_settings
from app.api.dependencies import get_current_user
from app.api.periods import optional_period
from app.db.session import get_db_session
from app.domain.periods import DateRange
from app.models.user import User
from app.ports.product_matching import ProductMatcherPort
from app.schemas.product import (
    ExplorationResponse,
    MergeProductsRequest,
    ProductResponse,
    ProductsOverviewResponse,
    RenameProductRequest,
    SelectionRequest,
    SelectionResponse,
    SplitProductRequest,
)
from app.services.product import ProductService

router = APIRouter(prefix="/api/v1/products", tags=["products"])


def get_product_matcher() -> ProductMatcherPort:
    """Provide the product matcher port; tests override this to stay off the network."""
    return ProductMatchingAdapter(agent_from_settings())


def get_product_service(
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
    matcher: Annotated[ProductMatcherPort, Depends(get_product_matcher)],
) -> ProductService:
    """The product service bound to the request's session."""
    return ProductService(session, matcher)


Service = Annotated[ProductService, Depends(get_product_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]


async def _listed(service: ProductService, user: User, search: str) -> list[ProductResponse]:
    summaries = await service.list_products(user.id, search)
    await service.session.commit()
    return [ProductResponse.model_validate(asdict(s)) for s in summaries]


@router.get("/explore", response_model=ExplorationResponse)
async def explore_products(
    current_user: CurrentUser,
    service: Service,
    product_ids: Annotated[list[uuid.UUID], Query(min_length=1, max_length=20)],
    period: Annotated[DateRange | None, Depends(optional_period)],
) -> ExplorationResponse:
    """How much of these products the caller bought, at what prices, and where (F16.2).

    `start` and `end` bound the period, both days included (ADR-0012); without them, all
    time. Only counted receipts of the caller's own (N2): another user's product is 404.
    """
    exploration = await service.explore(current_user.id, product_ids, period)
    return ExplorationResponse.model_validate(asdict(exploration))


@router.get("/overview", response_model=ProductsOverviewResponse)
async def products_overview(
    current_user: CurrentUser,
    service: Service,
    period: Annotated[DateRange | None, Depends(optional_period)],
) -> ProductsOverviewResponse:
    """The caller's biggest price moves and each shop's standing over the period (F23.5).

    Without `start` and `end`, all time. Only the caller's counted receipts (N2).
    """
    return ProductsOverviewResponse.model_validate(
        asdict(await service.overview(current_user.id, period))
    )


@router.get("/selections", response_model=list[SelectionResponse])
async def list_selections(current_user: CurrentUser, service: Service) -> list[SelectionResponse]:
    """The caller's saved selections, by name (F16.2)."""
    return [
        SelectionResponse.model_validate(s)
        for s in await service.products.selections(current_user.id)
    ]


@router.post("/selections", response_model=SelectionResponse, status_code=status.HTTP_201_CREATED)
async def create_selection(
    request: SelectionRequest, current_user: CurrentUser, service: Service
) -> SelectionResponse:
    """Save products under a name (F16.2). Another user's product is 404 (N2)."""
    selection = await service.save_selection(current_user.id, request.name, request.product_ids)
    await service.session.commit()
    return SelectionResponse.model_validate(selection)


@router.put("/selections/{selection_id}", response_model=SelectionResponse)
async def update_selection(
    selection_id: uuid.UUID, request: SelectionRequest, current_user: CurrentUser, service: Service
) -> SelectionResponse:
    """Rename a saved selection or change its products (F16.2). Another user's is 404 (N2)."""
    selection = await service.save_selection(
        current_user.id, request.name, request.product_ids, selection_id
    )
    await service.session.commit()
    return SelectionResponse.model_validate(selection)


@router.delete("/selections/{selection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_selection(
    selection_id: uuid.UUID, current_user: CurrentUser, service: Service
) -> Response:
    """Forget a saved selection (F16.2). Another user's is 404 (N2)."""
    await service.delete_selection(current_user.id, selection_id)
    await service.session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=list[ProductResponse])
async def list_products(
    current_user: CurrentUser,
    service: Service,
    search: Annotated[str, Query(max_length=100)] = "",
) -> list[ProductResponse]:
    """The products the caller buys, most bought first, with how each is printed (F16.1).

    Lines not matched to a product yet are matched first, so receipts stored before
    products existed appear too. Only the caller's own receipts (N2).
    """
    return await _listed(service, current_user, search)


@router.post("/{product_id}/merge", response_model=list[ProductResponse])
async def merge_products(
    product_id: uuid.UUID,
    request: MergeProductsRequest,
    current_user: CurrentUser,
    service: Service,
) -> list[ProductResponse]:
    """Fold other products into this one, with their lines and ways of printing (F16.1).

    Answers with the products list as it now is. Another user's product is not found (N2).
    """
    await service.merge(current_user.id, product_id, request.product_ids)
    return await _listed(service, current_user, "")


@router.patch("/{product_id}", response_model=list[ProductResponse])
async def rename_product(
    product_id: uuid.UUID,
    request: RenameProductRequest,
    current_user: CurrentUser,
    service: Service,
) -> list[ProductResponse]:
    """Give a product the name it is shown under (F16.1); receipts keep matching it.

    Answers with the products list as it now is. Another user's product is not found (N2).
    """
    await service.rename(current_user.id, product_id, request.name)
    return await _listed(service, current_user, "")


@router.post("/{product_id}/split", response_model=list[ProductResponse])
async def split_product(
    product_id: uuid.UUID, request: SplitProductRequest, current_user: CurrentUser, service: Service
) -> list[ProductResponse]:
    """Take one way of printing out of this product into a product of its own (F16.1).

    Answers with the products list as it now is. Another user's product is not found
    (N2); a product printed one way only cannot be split (400).
    """
    try:
        await service.split(current_user.id, product_id, request.alias_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return await _listed(service, current_user, "")
