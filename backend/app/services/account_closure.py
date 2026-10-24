"""Deleting an account and everything held about its owner (F17.9.1, GDPR art. 17)."""

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import PermissionDeniedError, ProblemCode
from app.core.security import verify_password
from app.models.user import User
from app.repository.household import HouseholdRepository
from app.services.household import HouseholdService


def _proves_owner(user: User, password: str) -> bool:
    """The password, or for an account without one (F1.6) its own address typed out."""
    if user.password_set:
        return verify_password(password, user.password_hash)
    return password.strip().lower() == user.email.lower()


def stored_prefixes(user: User) -> list[str]:
    """Where the account's files live in object storage: its photos and its exports."""
    return [f"receipts/{user.id}/", f"exports/{user.id}/"]


class AccountClosureService:
    """Removes an account: its rows by the database's cascades, its place in a household.

    Every table holding something of the user's references the account with ON DELETE
    CASCADE, so deleting the user row deletes receipts and their lines, trips, goals,
    advice, categories and rules, products, selections, exports, upload jobs and
    sessions in one statement. The files are the caller's to delete afterwards, under
    `stored_prefixes`, once the deletion is committed.
    """

    def __init__(
        self,
        session: AsyncSession,
        before_closing: Callable[[User], Awaitable[None]] | None = None,
    ) -> None:
        """`before_closing` runs once the owner is proven, e.g. revoking Apple's tokens."""
        self.session = session
        self.before_closing = before_closing

    async def close(self, user: User, password: str) -> list[str]:
        """Delete `user` once the password proves it is them; returns the file prefixes.

        Raises PermissionDeniedError (invalid_credentials) for a wrong password, so a
        screen left signed in cannot delete the account.
        """
        if not _proves_owner(user, password):
            raise PermissionDeniedError(
                "The password is not right.", code=ProblemCode.INVALID_CREDENTIALS
            )
        if self.before_closing is not None:
            await self.before_closing(user)
        await HouseholdService(HouseholdRepository(self.session)).depart(user)
        prefixes = stored_prefixes(user)
        await self.session.delete(user)
        await self.session.flush()
        return prefixes
