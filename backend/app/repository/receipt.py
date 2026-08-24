from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession


class ReceiptRepository:
    """Data access for Receipt entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def exists_for_user(self, user_id: UUID) -> bool:
        """Check if any receipts exist for the given user.

        Returns False if the receipts table does not exist yet (pre-Epic E2).
        """
        try:
            async with self.session.begin_nested():
                stmt = text("SELECT 1 FROM receipts WHERE user_id = :user_id LIMIT 1")
                result = await self.session.execute(stmt, {"user_id": user_id})
                return result.scalar() is not None
        except ProgrammingError:
            return False
