"""Households and memberships (F12.2, ADR-0017)."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.household import Household, HouseholdMember


class HouseholdRepository:
    """Data access for households, reached only through a user's own membership.

    Households carry no `user_id`, so the ownership filter of `BaseRepository` does not
    apply; every lookup starts from the asking user's membership row instead, which is
    what keeps one household's data out of another's reach (N2).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def membership_of(self, user_id: uuid.UUID) -> HouseholdMember | None:
        """The user's membership, with its household and members loaded, if they have one."""
        stmt = (
            select(HouseholdMember)
            .where(HouseholdMember.user_id == user_id)
            .options(
                joinedload(HouseholdMember.household)
                .selectinload(Household.members)
                .joinedload(HouseholdMember.user)
            )
            # Members are added and removed under a session that may hold this household
            # already; a stale collection would show someone who has left.
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).unique().scalar_one_or_none()

    async def by_invite_code(self, code: str) -> Household | None:
        """The household whose current invite link carries `code`, with its members."""
        stmt = (
            select(Household)
            .where(Household.invite_code == code)
            .options(selectinload(Household.members).joinedload(HouseholdMember.user))
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def add_member(self, household: Household, member: HouseholdMember) -> None:
        """Put a user into a household."""
        household.members.append(member)
        await self.session.flush()

    async def add(self, household: Household) -> None:
        """Store a new household with the members it was given."""
        self.session.add(household)
        await self.session.flush()

    async def remove_member(self, member: HouseholdMember) -> None:
        """Take one membership away; the household itself stays."""
        await self.session.delete(member)
        await self.session.flush()

    async def delete(self, household: Household) -> None:
        """Delete a household and every membership in it; no receipt is touched."""
        await self.session.delete(household)
        await self.session.flush()
