from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.models.user import User
from app.repository.category import CategoryRepository
from app.schemas.category import CategoryOut

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
