import secrets
from typing import ClassVar

from polyfactory import Use

from app.models.household import Household, HouseholdMember, HouseholdRole
from tests.factories.base import ModelFactory


class HouseholdFactory(ModelFactory[Household]):
    """A named household with nobody in it; tests add members with HouseholdMemberFactory."""

    __model__ = Household

    name = Use(lambda: "Home")
    invite_code = Use(lambda: secrets.token_hex(16))
    # No budget unless a test about the household budget sets one (F12.5).
    budget_limit = None
    members: ClassVar[list[HouseholdMember]] = []


class HouseholdMemberFactory(ModelFactory[HouseholdMember]):
    """An ordinary member unless a test makes them the owner (ADR-0017)."""

    __model__ = HouseholdMember
    # Generated `household` and `user` objects would overwrite the ids a test passes in.
    __set_relationships__ = False

    role = Use(lambda: HouseholdRole.MEMBER.value)
