import uuid
from collections.abc import Sequence

from app.api.errors import InvalidGoalError, NotFoundError
from app.domain.goals import GoalShape, GoalType, InvalidGoal, check_goal, clean_item_names
from app.models.goal import Goal
from app.ports.goal_mapping import GoalMapperPort
from app.repository.category import CategoryRepository
from app.repository.goal import GoalRepository
from app.schemas.goal import GoalCreate, GoalUpdate

_NOT_CLEARABLE = {
    "name": "A goal needs a name.",
    "mapped_category_ids": "Send an empty list to stop watching every category.",
    "mapped_item_names": "Send an empty list to stop watching every item.",
}


class GoalService:
    """The user's goals: stating, changing and dropping them (BRD F1, F9 — F8.1, F8.2).

    A lifestyle goal is handed to the mapper when it is stated, and again when its
    wording changes, to choose the spending lines it watches — until the user
    corrects that list, after which it is theirs and no automatic pass touches it.
    """

    def __init__(
        self,
        goals: GoalRepository,
        categories: CategoryRepository,
        mapper: GoalMapperPort,
    ) -> None:
        self.goals = goals
        self.categories = categories
        self.mapper = mapper

    async def list(self) -> Sequence[Goal]:
        """The user's goals, newest first."""
        return await self.goals.list_mine()

    async def create(self, user_id: uuid.UUID, request: GoalCreate) -> Goal:
        """Record a goal once its parts fit together; map a lifestyle one (BRD F1, F9).

        Raises InvalidGoalError for a malformed goal or a category they cannot use.
        """
        goal = Goal(user_id=user_id, **request.model_dump())
        await self._check(goal, user_id)
        if goal.type == GoalType.LIFESTYLE:
            await self._map(goal, user_id)
        self.goals.add(goal)
        await self.goals.session.flush()
        await self.goals.session.refresh(goal)
        return goal

    async def update(self, user_id: uuid.UUID, goal_id: uuid.UUID, request: GoalUpdate) -> Goal:
        """Change only the fields sent; the goal as changed must still be well formed.

        Sending `mapped_*` is the user correcting what the goal watches, which
        stops later automatic passes. Otherwise a lifestyle goal whose name or
        description actually changed is mapped again.

        Raises NotFoundError for a goal that is not the user's (N2), and
        InvalidGoalError when the change would break it or clear a required field.
        """
        goal = await self._mine(goal_id)
        changes = request.model_dump(exclude_unset=True)
        for field, reason in _NOT_CLEARABLE.items():
            if field in changes and changes[field] is None:
                raise InvalidGoalError(reason)
        if "mapped_item_names" in changes:
            changes["mapped_item_names"] = clean_item_names(changes["mapped_item_names"])
        if "mapped_category_ids" in changes:
            changes["mapped_category_ids"] = list(dict.fromkeys(changes["mapped_category_ids"]))

        wording = (goal.name, goal.description)
        for field, value in changes.items():
            setattr(goal, field, value)
        if changes.keys() & {"mapped_category_ids", "mapped_item_names"}:
            goal.mapping_set_by_user = True
        await self._check(goal, user_id)

        reworded = (goal.name, goal.description) != wording
        if goal.type == GoalType.LIFESTYLE and reworded and not goal.mapping_set_by_user:
            await self._map(goal, user_id)
        await self.goals.session.flush()
        await self.goals.session.refresh(goal)
        return goal

    async def delete(self, goal_id: uuid.UUID) -> None:
        """Drop a goal; raises NotFoundError for one that is not the user's (N2)."""
        goal = await self._mine(goal_id)
        await self.goals.session.delete(goal)
        await self.goals.session.flush()

    async def _mine(self, goal_id: uuid.UUID) -> Goal:
        goal = await self.goals.get(goal_id)
        if goal is None:
            raise NotFoundError("Goal not found")
        return goal

    async def _map(self, goal: Goal, user_id: uuid.UUID) -> None:
        categories = await self.categories.list_available(user_id)
        mapping = await self.mapper.map_goal(goal.name, goal.description, categories)
        goal.mapped_category_ids = mapping.mapped_category_ids
        goal.mapped_item_names = mapping.mapped_item_names

    async def _check(self, goal: Goal, user_id: uuid.UUID) -> None:
        watched_categories = goal.mapped_category_ids or []
        try:
            check_goal(
                GoalShape(
                    goal.type,
                    goal.financial_kind,
                    goal.target_amount,
                    goal.category_id,
                    watches_spending=bool(watched_categories or goal.mapped_item_names),
                )
            )
        except InvalidGoal as error:
            raise InvalidGoalError(str(error)) from error
        # Another user's custom category is not theirs to aim at or to watch (N2).
        if goal.category_id and not await self.categories.get_available(goal.category_id, user_id):
            raise InvalidGoalError("That category is not one of yours.")
        if watched_categories:
            available = {c.id for c in await self.categories.list_available(user_id)}
            if not set(watched_categories) <= available:
                raise InvalidGoalError("That category is not one of yours.")
