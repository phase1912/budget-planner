"""The household rules: one per user, an owner who manages it, members who may leave,
and joining by the owner's invite link (F12.2, F12.3, ADR-0017)."""

import secrets
import uuid
from decimal import Decimal

from app.api.errors import DomainError, NotFoundError, PermissionDeniedError
from app.models.household import Household, HouseholdMember, HouseholdRole
from app.models.user import User
from app.repository.household import HouseholdRepository
from app.repository.receipt import HouseholdReaders, ReceiptRepository


class HouseholdService:
    """Creates, renames and dissolves households and moves people out of them.

    Every operation acts on the caller's own household, found from their membership, so
    no request can name someone else's (N2) — except joining, which names one by the
    secret code in its invite link.
    """

    def __init__(self, households: HouseholdRepository) -> None:
        self.households = households
        self.receipts = ReceiptRepository(households.session).bypass_ownership()

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

    async def readers(self, user: User) -> HouseholdReaders | None:
        """Whose receipts the user may read through their household, or None outside one.

        Read from their membership now, so a member who has left or been removed reads
        nothing of the household's from the next request on (ADR-0017, N2).
        """
        membership = await self.households.membership_of(user.id)
        if membership is None:
            return None
        members = frozenset(m.user_id for m in membership.household.members)
        return HouseholdReaders(reader_id=user.id, member_ids=members)

    async def set_budget(self, user: User, limit: Decimal | None) -> Household:
        """Set or clear what the household means to spend a month (owner only, D7).

        Like a personal limit it is presentation only: months are measured against it
        as it stands, never rewritten by it.
        """
        membership = await self._owned_by(user)
        membership.household.budget_limit = limit
        return membership.household

    async def regenerate_invite(self, user: User) -> Household:
        """Give the household a new invite link; the old one stops working at once (owner)."""
        membership = await self._owned_by(user)
        membership.household.invite_code = secrets.token_hex(16)
        return membership.household

    async def invited_to(self, code: str) -> Household:
        """The household an invite link leads to, for the person deciding whether to join.

        Raises NotFoundError for a code that is not, or no longer, any household's.
        """
        household = await self.households.by_invite_code(code)
        if household is None:
            raise NotFoundError("This invite link is not valid. Ask for a new one.")
        return household

    async def join(self, user: User, code: str) -> Household:
        """Put the caller into the household the invite link leads to, as a member.

        Refused (DomainError) when they already belong to a household — one each — or
        when their account currency is not the household's, since its totals are in one
        currency (ADR-0017, ADR-0016). An account with no receipts yet, such as one just
        registered from the invite link, takes the household's currency instead.
        """
        household = await self.invited_to(code)
        if await self.households.membership_of(user.id):
            raise DomainError("You already belong to a household; leave it to join another.")
        currency = _currency_of(household)
        if currency is not None and user.currency != currency:
            # A new account has had no reason to pick a currency yet; it takes the
            # household's, as it could on Profile, since no receipt is in the old one.
            if not await self.receipts.exists_for_user(user.id):
                user.currency = currency
            else:
                raise DomainError(
                    f"This household keeps its budget in {currency} and your account is in "
                    f"{user.currency}. Only accounts in the same currency can share a budget."
                )
        await self.households.add_member(
            household, HouseholdMember(user_id=user.id, role=HouseholdRole.MEMBER)
        )
        return await self._household(user)

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


def _currency_of(household: Household) -> str | None:
    """The currency the household's totals are in: its members' (ADR-0017)."""
    return household.members[0].user.currency if household.members else None
