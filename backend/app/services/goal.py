import uuid
from collections.abc import Sequence

from app.api.errors import InvalidGoalError, NotFoundError
from app.domain.goals import GoalShape, InvalidGoal, check_goal
from app.models.goal import Goal
from app.repository.category import CategoryRepository
from app.repository.goal import GoalRepository
from app.schemas.goal import GoalCreate, GoalUpdate


class GoalService:
    """The user's goals: stating, changing and dropping them (BRD F1 — F8.1)."""

    def __init__(self, goals: GoalRepository, categories: CategoryRepository) -> None:
        self.goals = goals
        self.categories = categories

    async def list(self) -> Sequence[Goal]:
        """The user's goals, newest first."""
        return await self.goals.list_mine()

    async def create(self, user_id: uuid.UUID, request: GoalCreate) -> Goal:
        """Record a goal once its parts fit together and its category is the user's to use.

        Raises InvalidGoalError for a malformed goal or a category they cannot use.
        """
        goal = Goal(user_id=user_id, **request.model_dump())
        await self._check(goal, user_id)
        self.goals.add(goal)
        await self.goals.session.flush()
        await self.goals.session.refresh(goal)
        return goal

    async def update(self, user_id: uuid.UUID, goal_id: uuid.UUID, request: GoalUpdate) -> Goal:
        """Change only the fields sent; the goal as changed must still be well formed.

        Raises NotFoundError for a goal that is not the user's (N2), and
        InvalidGoalError when the change would break it or clear its name.
        """
        goal = await self._mine(goal_id)
        changes = request.model_dump(exclude_unset=True)
        if "name" in changes and changes["name"] is None:
            raise InvalidGoalError("A goal needs a name.")
        for field, value in changes.items():
            setattr(goal, field, value)
        await self._check(goal, user_id)
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

    async def _check(self, goal: Goal, user_id: uuid.UUID) -> None:
        try:
            check_goal(
                GoalShape(goal.type, goal.financial_kind, goal.target_amount, goal.category_id)
            )
        except InvalidGoal as error:
            raise InvalidGoalError(str(error)) from error
        if goal.category_id and not await self.categories.get_available(goal.category_id, user_id):
            # Another user's custom category is not theirs to aim at (N2).
            raise InvalidGoalError("That category is not one of yours.")
