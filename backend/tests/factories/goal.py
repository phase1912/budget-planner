import uuid
from decimal import Decimal

from polyfactory import Use

from app.domain.goals import FinancialKind, GoalType
from app.models.goal import Goal
from tests.factories.base import ModelFactory


class GoalFactory(ModelFactory[Goal]):
    """A well formed spending-ceiling goal unless told otherwise (BRD F1)."""

    __model__ = Goal

    type = Use(lambda: GoalType.FINANCIAL)
    financial_kind = Use(lambda: FinancialKind.SPENDING_CEILING)
    name = Use(lambda: "Stay under 3 000 PLN a month")
    description = None
    target_amount = Use(lambda: Decimal("3000.00"))
    category_id = None
    mapped_category_ids = Use(lambda: list[uuid.UUID]())
    mapped_item_names = Use(lambda: list[str]())
    mapping_set_by_user = False
    warning_dismissed_for = None
