"""The household rules: one per user, an owner who manages it, members who may leave
(F12.2, ADR-0017)."""

import uuid

from app.api.errors import DomainError, NotFoundError, PermissionDeniedError
from app.models.household import Household, HouseholdMember, HouseholdRole
from app.models.user import User
from app.repository.household import HouseholdRepository


class HouseholdService:
    """Creates, renames and dissolves households and moves people out of them.

    Every operation acts on the caller's own household, found from their membership, so
    no request can name someone else's (N2). Joining is F12.3's.
    """

    def __init__(self, households: HouseholdRepository) -> None:
        self.households = households

    async def mine(self, user: User) -> Household | None:
        """The caller's household, or None when they belong to none."""
        membership = await self.households.membership_of(user.id)
        return membership.household if membership else None

    async def create(self, user: User, name: str) -> Household:
        """Start a household with the caller as its owner.

        Raises DomainError when they already belong to one: a user has one household,
        so every receipt counts towards one shared budget at most (ADR-0017).
        """
        if await self.households.membership_of(user.id):
            raise DomainError("You already belong to a household; leave it first.")
        household = Household(
            name=name, members=[HouseholdMember(user_id=user.id, role=HouseholdRole.OWNER)]
        )
        await self.households.add(household)
        return await self._household(user)

    async def rename(self, user: User, name: str) -> Household:
        """Rename the caller's household; only its owner may (PermissionDeniedError)."""
        membership = await self._owned_by(user)
        membership.household.name = name
        return membership.household

    async def leave(self, user: User) -> None:
        """Take the caller out of their household.

        The owner may not leave others behind without anyone to manage it (DomainError);
        the last one out deletes the household. Their receipts were always theirs, so
        they simply stop being read by the others.
        """
        membership = await self._membership(user)
        household = membership.household
        if len(household.members) == 1:
            await self.households.delete(household)
            return
        if membership.role == HouseholdRole.OWNER:
            raise DomainError("Remove the other members before leaving the household you own.")
        await self.households.remove_member(membership)

    async def remove_member(self, user: User, member_user_id: uuid.UUID) -> Household:
        """The owner takes someone out of the household; their access ends at once.

        A user who is not in the caller's household is not found (N2); the owner removes
        themselves by leaving, never here (DomainError).
        """
        membership = await self._owned_by(user)
        if member_user_id == user.id:
            raise DomainError("Leave the household instead of removing yourself.")
        target = next(
            (m for m in membership.household.members if m.user_id == member_user_id), None
        )
        if target is None:
            raise NotFoundError("No such member in your household.")
        await self.households.remove_member(target)
        membership.household.members.remove(target)
        return membership.household

    async def _household(self, user: User) -> Household:
        return (await self._membership(user)).household

    async def _membership(self, user: User) -> HouseholdMember:
        membership = await self.households.membership_of(user.id)
        if membership is None:
            raise NotFoundError("You do not belong to a household.")
        return membership

    async def _owned_by(self, user: User) -> HouseholdMember:
        membership = await self._membership(user)
        if membership.role != HouseholdRole.OWNER:
            raise PermissionDeniedError("Only the household's owner can do this.")
        return membership
