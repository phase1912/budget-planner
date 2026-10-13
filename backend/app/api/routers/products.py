import uuid
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.product_matching_agent import ProductMatchingAdapter
from app.agent.factory import agent_from_settings
from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.models.user import User
from app.ports.product_matching import ProductMatcherPort
from app.schemas.product import MergeProductsRequest, ProductResponse, SplitProductRequest
from app.services.product import ProductService

router = APIRouter(prefix="/api/v1/products", tags=["products"])


def get_product_matcher() -> ProductMatcherPort:
    """Provide the product matcher port; tests override this to stay off the network."""
    return ProductMatchingAdapter(agent_from_settings())


def get_product_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
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
