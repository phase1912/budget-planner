import uuid
from collections.abc import Sequence as ABCSequence
from typing import Any, TypeVar

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.core.context import current_user_id

ModelType = TypeVar("ModelType", bound=DeclarativeBase)


class BaseRepository[ModelType: DeclarativeBase]:
    """Ownership-enforcing repository base class (F1.3.2).

    Automatically scopes queries to the current user id from `app.context.current_user_id`.
    Bypassing it requires setting `_bypass_ownership_check=True`.
    """

    def __init__(self, model_class: type[ModelType], session: AsyncSession) -> None:
        self.model_class = model_class
        self.session = session
        # Escape hatch to explicitly allow cross-user queries if ever needed.
        # Should be used sparingly and greppable.
        self._bypass_ownership_check = False

    def bypass_ownership(self) -> "BaseRepository[ModelType]":
        """Explicitly disable the ownership filter for this repository instance."""
        self._bypass_ownership_check = True
        return self

    def _apply_ownership(self, stmt: Any) -> Any:
        if self._bypass_ownership_check:
            return stmt

        # Check if model has user_id column
        if not hasattr(self.model_class, "user_id"):
            # If the entity doesn't have a user_id (e.g. User itself), no filter applies here.
            # But normally we only use this base repo for user-owned resources.
            return stmt

        uid = current_user_id.get()
        if not uid:
            from app.api.errors import AuthenticationError

            raise AuthenticationError("No user context available for ownership filtering.")

        return stmt.where(self.model_class.user_id == uid)  # type: ignore[attr-defined]

    async def get(self, id: uuid.UUID) -> ModelType | None:
        stmt = select(self.model_class).where(self.model_class.id == id)  # type: ignore[attr-defined]
        stmt = self._apply_ownership(stmt)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list(self) -> ABCSequence[ModelType]:
        stmt = select(self.model_class)
        stmt = self._apply_ownership(stmt)
        return (await self.session.execute(stmt)).scalars().all()

    async def delete(self, id: uuid.UUID) -> bool:
        stmt = delete(self.model_class).where(self.model_class.id == id)  # type: ignore[attr-defined]
        stmt = self._apply_ownership(stmt)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0  # type: ignore[attr-defined, no-any-return]

    def add(self, obj: ModelType) -> None:
        if not self._bypass_ownership_check and hasattr(self.model_class, "user_id"):
            uid = current_user_id.get()
            if not uid:
                from app.api.errors import AuthenticationError

                raise AuthenticationError("No user context available for ownership filtering.")
            # Automatically assign ownership if not set, or ensure it matches
            obj_user_id = getattr(obj, "user_id", None)
            if obj_user_id is None:
                obj.user_id = uid  # type: ignore[attr-defined]
            elif obj_user_id != uid:
                from app.api.errors import PermissionDeniedError

                raise PermissionDeniedError("Cannot create records owned by another user.")
        self.session.add(obj)
