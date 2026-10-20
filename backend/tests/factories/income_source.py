from decimal import Decimal

from polyfactory import Use

from app.models.income_source import IncomeSource
from tests.factories.base import ModelFactory


class IncomeSourceFactory(ModelFactory[IncomeSource]):
    """A regular income of the user's own, on no account, untaxed, exactly its amount."""

    __model__ = IncomeSource

    name = Use(lambda: "Salary")
    amount = Use(lambda: Decimal("9000.00"))
    day = None
    weekday = None
    ends_on = None
    household_id = None
    account_id = None
    taxed = False
    about = False
