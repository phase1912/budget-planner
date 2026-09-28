from sqlalchemy.ext.asyncio import AsyncSession

from app.models.export_job import ExportJob
from app.repository.base import BaseRepository


class ExportJobRepository(BaseRepository[ExportJob]):
    """The current user's exports (BRD N6); another user's reads as not found (N2)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model_class=ExportJob, session=session)
