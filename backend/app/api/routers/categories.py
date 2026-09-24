import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.models.user import User
from app.repository.category import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.services.taxonomy import TaxonomyService

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


def get_category_repository(
    session: AsyncSession = Depends(get_db_session),
) -> CategoryRepository:
    """Provide the taxonomy repository bound to the request's session."""
    return CategoryRepository(session)


@router.get("", response_model=list[CategoryOut])
async def list_categories(
    current_user: User = Depends(get_current_user),
    repository: CategoryRepository = Depends(get_category_repository),
) -> list[CategoryOut]:
    """List the taxonomy — built-in and custom — with this user's totals (BRD C1, C2)."""
    categories = await repository.list_with_statistics(current_user.id)
    return [CategoryOut.model_validate(category) for category in categories]


@router.post("", response_model=CategoryOut, status_code=201)
async def create_category(
    payload: CategoryCreate,
    current_user: User = Depends(get_current_user),
    repository: CategoryRepository = Depends(get_category_repository),
) -> CategoryOut:
    """Create a custom category, available to the picker and the agent at once (BRD C6)."""
    category = await TaxonomyService(repository).create(current_user.id, payload.name)
    return CategoryOut(
        id=category.id, name=category.name, is_builtin=False, item_count=0, total_amount=0
    )


@router.patch("/{category_id}", response_model=CategoryOut)
async def rename_category(
    category_id: uuid.UUID,
    payload: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    repository: CategoryRepository = Depends(get_category_repository),
) -> CategoryOut:
    """Rename one of the caller's own categories (BRD C6)."""
    category = await TaxonomyService(repository).rename(category_id, current_user.id, payload.name)
    stats = await repository.list_with_statistics(current_user.id)
    return CategoryOut.model_validate(next(s for s in stats if s.id == category.id))


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: uuid.UUID,
    move_to_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    repository: CategoryRepository = Depends(get_category_repository),
) -> None:
    """Delete one of the caller's categories, moving its items to `move_to_id` (BRD C7)."""
    await TaxonomyService(repository).delete(category_id, current_user.id, move_to_id)
