"""Reading what a user owns together with what their household shares (F12.8)."""

from typing import Any

from sqlalchemy import or_, select

from app.core.context import current_user_id
from app.models.household import HouseholdMember
from app.repository.base import BaseRepository


class SharedWithHousehold[ModelType](BaseRepository[ModelType]):  # type: ignore[type-var]
    """Ownership widened to the caller's household, for money a family shares (F12.8).

    A row is visible, and changeable, when the caller wrote it or when it is shared with
    the household the caller belongs to (`household_id`). Leaving the household ends that
    at once: the membership the filter reads is gone (ADR-0017, N2).
    """

    def _apply_ownership(self, stmt: Any) -> Any:
        if self._bypass_ownership_check:
            return stmt
        uid = current_user_id.get()
        if not uid:
            from app.api.errors import AuthenticationError

            raise AuthenticationError("No user context available for ownership filtering.")
        model: Any = self.model_class
        households = select(HouseholdMember.household_id).where(HouseholdMember.user_id == uid)
        return stmt.where(or_(model.user_id == uid, model.household_id.in_(households)))
