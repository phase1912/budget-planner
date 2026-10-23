"""Settings and the family by chat (F21.11, ADR-0029): each change a card showing the
setting as it is and as it will be, saved through the Settings screen's own services.

Password, email, the second factor and deleting the account have no tool: they stay on
their screens, and the prompt points there.
"""

import json
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, get_args

from pydantic import BaseModel, Field, ValidationError

from app.api.errors import NotFoundError
from app.assistant.tools.base import (
    Answer,
    FormField,
    Reader,
    ToolContext,
    Writer,
    as_id,
    find_by_name,
)
from app.models.household import Household, HouseholdMember, HouseholdRole
from app.repository.household import HouseholdRepository
from app.schemas.user import UserUpdateRequest
from app.services.household import HouseholdService
from app.services.user import UserService

Setting = Literal[
    "currency",
    "usual_income",
    "payday",
    "starting_balance",
    "pays_own_taxes",
    "tax_rate",
    "tax_fixed_monthly",
    "language",
    "palette",
    "dark_at_night",
    "travels_for_work",
]
SETTINGS: tuple[str, ...] = get_args(Setting)
SWITCHES = {"pays_own_taxes", "dark_at_night", "travels_for_work"}
NUMBERS = {"usual_income", "starting_balance", "tax_rate", "tax_fixed_monthly"}
ON = {"on", "yes", "true", "1"}
OFF = {"off", "no", "false", "0"}


class NoArgs(BaseModel):
    """Nothing to say: the tool reads the whole of it."""


DEFAULTS: dict[str, Any] = {"palette": "midnight", "language": "en"}
"""What an account that never chose one sees: Midnight is the default look (F23.1)."""


def _current(ctx: ToolContext) -> dict[str, Any]:
    user = ctx.user
    return {
        name: value if (value := getattr(user, name, None)) is not None else DEFAULTS.get(name)
        for name in SETTINGS
    }


def _shown(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "on" if value else "off"
    return str(value)


def _parsed(setting: str, said: str) -> Any:
    """The value as the Settings screen would send it; ValueError when it cannot be."""
    word = said.strip().lower()
    if setting in SWITCHES:
        if word in ON:
            return True
        if word in OFF:
            return False
        raise ValueError("say on or off")
    if setting in NUMBERS:
        try:
            return Decimal(word.replace(",", ".").replace(" ", ""))
        except InvalidOperation as error:
            raise ValueError("a number") from error
    if setting == "payday":
        return int(word)
    if setting == "currency":
        return said.strip().upper()
    return word


def _request(setting: str, said: str) -> UserUpdateRequest:
    """The one-setting change, checked by the same rules as the screen's; raises ValueError."""
    try:
        return UserUpdateRequest.model_validate({setting: _parsed(setting, said)})
    except ValidationError as error:
        raise ValueError(error.errors()[0]["msg"]) from error


class Settings(Reader):
    """What the user has set on the Settings screen, for "what is my payday?" (F21.11)."""

    name = "settings"
    description = (
        "The user's settings: currency, usual income, payday, starting balance, own taxes and "
        "their rate, language, palette, dark at night, travels for work."
    )
    args = NoArgs

    async def read(self, ctx: ToolContext, args: NoArgs) -> Answer:
        current = {k: _shown(v) for k, v in _current(ctx).items()}
        return Answer(json.dumps(current), {"screen": "settings", "to": "/settings"})


class SettingArgs(BaseModel):
    """One setting and what it becomes, as the user said it."""

    setting: Setting
    value: str = Field(
        min_length=1,
        max_length=40,
        description=(
            "language en, uk or pl; palette midnight, daylight, rose, lavender, sage or ocean; "
            "switches on or off; payday 1-31 (31 the last day); amounts as plain numbers"
        ),
    )


class SettingCard(BaseModel):
    """A setting's change as the user approves it."""

    target: str
    setting: Setting
    value: str = Field(min_length=1, max_length=40)


class ChangeSetting(Writer):
    """A card changing one setting, saved as from Settings; several settings are several
    cards. A currency change is refused once receipts exist, as on the screen (F1.4.2)."""

    name = "change_setting"
    description = (
        "Propose changing one of the user's settings — currency, usual income, payday, "
        "starting balance, own taxes or their rate or fixed sum, language, palette, dark at "
        "night, travels for work. One call per setting."
    )
    args = SettingArgs
    card_kind = "setting"
    card = SettingCard
    form = (FormField("target", "target"), FormField("value", "text"))

    async def check(self, ctx: ToolContext, args: SettingArgs) -> str | None:
        try:
            _request(args.setting, args.value)
        except ValueError as error:
            return f"{args.setting} cannot be {args.value!r}: {error}"
        return None

    async def propose(self, ctx: ToolContext, args: SettingArgs) -> dict[str, Any]:
        before = _shown(_current(ctx)[args.setting])
        after = _shown(
            _request(args.setting, args.value).model_dump(exclude_unset=True)[args.setting]
        )
        return {
            "target": f"{args.setting}: {before} → {after}",
            "setting": args.setting,
            "value": args.value,
        }

    async def save(self, ctx: ToolContext, fields: SettingCard) -> str:
        try:
            request = _request(fields.setting, fields.value)
        except ValueError as error:
            raise NotFoundError(f"{fields.setting} cannot be {fields.value!r}: {error}") from error
        await UserService(ctx.session).update_profile(ctx.user, request)
        return f"setting:{fields.setting}"


async def _family(ctx: ToolContext) -> Household | None:
    return await HouseholdService(HouseholdRepository(ctx.session)).mine(ctx.user)


def _role(member: HouseholdMember) -> str:
    if member.role == HouseholdRole.OWNER:
        return "owner"
    return "child" if member.role == HouseholdRole.CHILD else "adult"


class Family(Reader):
    """Who is in the user's family and as what, and the invite code to share (F12, F21.11)."""

    name = "family"
    description = "The user's family: its name, each member and their role, and the invite code."
    args = NoArgs

    async def read(self, ctx: ToolContext, args: NoArgs) -> Answer:
        household = await _family(ctx)
        if household is None:
            return Answer(json.dumps({"family": None}), {"screen": "settings", "to": "/settings"})
        figures = {
            "family": household.name,
            "members": [
                {"name": m.user.first_name, "role": _role(m), "you": m.user_id == ctx.user.id}
                for m in household.members
            ],
            "invite": "shared from Settings → Family as a link; the assistant cannot send it",
        }
        return Answer(json.dumps(figures), {"screen": "settings", "to": "/settings"})


class MemberArgs(BaseModel):
    """A member of the user's family, by first name."""

    member: str = Field(min_length=1, max_length=80, description="Their first name")


class RoleArgs(MemberArgs):
    """A member and what they are to be."""

    role: Literal["adult", "child"]


class MemberCard(BaseModel):
    """A change to one member, as the user approves it."""

    target: str
    member_id: str
    role: Literal["adult", "child"] | None = None


async def _member(ctx: ToolContext, said: str) -> tuple[HouseholdMember | None, str | None]:
    household = await _family(ctx)
    if household is None:
        return None, "the user has no family"
    others = [m for m in household.members if m.user_id != ctx.user.id]
    found = find_by_name(others, said, lambda m: m.user.first_name)
    return found.item, found.error


class FamilyRole(Writer):
    """A card marking a member an adult or a child; only the family's owner may (F12.10)."""

    name = "family_role"
    description = "Propose marking a member of the user's family as an adult or a child."
    args = RoleArgs
    card_kind = "family_role"
    card = MemberCard
    form = (FormField("target", "target"), FormField("role", "choice", options=("adult", "child")))

    async def check(self, ctx: ToolContext, args: RoleArgs) -> str | None:
        return (await _member(ctx, args.member))[1]

    async def propose(self, ctx: ToolContext, args: RoleArgs) -> dict[str, Any]:
        member, _ = await _member(ctx, args.member)
        if member is None:
            raise NotFoundError("No such member in your household.")
        return {
            "target": f"{member.user.first_name}: {_role(member)} → {args.role}",
            "member_id": str(member.user_id),
            "role": args.role,
        }

    async def save(self, ctx: ToolContext, fields: MemberCard) -> str:
        await HouseholdService(HouseholdRepository(ctx.session)).set_role(
            ctx.user, as_id(fields.member_id), fields.role or "adult"
        )
        return f"member:{fields.member_id}"


class RemoveMember(Writer):
    """A card taking a member out of the family; only its owner may, and their shared money
    goes back to them (F12.8, F12.10)."""

    name = "family_remove"
    description = "Propose taking a member out of the user's family."
    args = MemberArgs
    card_kind = "family_remove"
    card = MemberCard
    form = (FormField("target", "target"),)

    async def check(self, ctx: ToolContext, args: MemberArgs) -> str | None:
        return (await _member(ctx, args.member))[1]

    async def propose(self, ctx: ToolContext, args: MemberArgs) -> dict[str, Any]:
        member, _ = await _member(ctx, args.member)
        if member is None:
            raise NotFoundError("No such member in your household.")
        return {"target": member.user.first_name, "member_id": str(member.user_id)}

    async def save(self, ctx: ToolContext, fields: MemberCard) -> str:
        await HouseholdService(HouseholdRepository(ctx.session)).remove_member(
            ctx.user, as_id(fields.member_id)
        )
        return f"member:{fields.member_id}"


class LeaveCard(BaseModel):
    """Leaving the family, as the user approves it."""

    target: str


class LeaveFamily(Writer):
    """A card taking the user out of their family; an owner with others in it is refused, as
    on the screen, and the last one out ends the family (F12)."""

    name = "family_leave"
    description = "Propose that the user leaves their family."
    args = NoArgs
    card_kind = "family_leave"
    card = LeaveCard
    form = (FormField("target", "target"),)

    async def check(self, ctx: ToolContext, args: NoArgs) -> str | None:
        return None if await _family(ctx) is not None else "the user has no family"

    async def propose(self, ctx: ToolContext, args: NoArgs) -> dict[str, Any]:
        household = await _family(ctx)
        return {"target": household.name if household else ""}

    async def save(self, ctx: ToolContext, fields: LeaveCard) -> str:
        await HouseholdService(HouseholdRepository(ctx.session)).leave(ctx.user)
        return "family:left"
