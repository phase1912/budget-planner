"""Domain entity mappings.

Import every model module here so `Base.metadata` is complete before Alembic's
`env.py` (autogenerate) or `create_all` (tests) inspect it. Empty until the first
epic (E1+) adds a concrete entity — F0.3 delivers only the base and conventions.
"""

from app.models.account import Account, AccountMove, RegularTransfer
from app.models.activity import ActivityEvent, PageViewCount
from app.models.admin import AdminAction, PlanGrant
from app.models.ai_usage import AiUsage
from app.models.base import Base, Model
from app.models.category import Category
from app.models.category_rule import CategoryRule
from app.models.conversation import Conversation, ConversationMessage
from app.models.exchange_rate import CachedExchangeRate
from app.models.export_job import ExportJob
from app.models.goal import Goal
from app.models.household import Household, HouseholdMember
from app.models.income import Income
from app.models.income_source import IncomeSource
from app.models.line_item import LineItem
from app.models.match_override import PositionMatchOverride
from app.models.monthly_snapshot import MonthlySnapshot
from app.models.name_correction import NameCorrection
from app.models.pending_income import PendingIncome
from app.models.product import Product, ProductAlias
from app.models.receipt import Receipt
from app.models.recommendation import Recommendation
from app.models.refresh_token import RefreshToken
from app.models.regular_expense import RegularExpense
from app.models.selection import ProductSelection
from app.models.tax_payment import TaxPayment
from app.models.trip import Trip
from app.models.upload_job import UploadJob
from app.models.user import User

__all__ = [
    "Account",
    "AccountMove",
    "ActivityEvent",
    "AdminAction",
    "AiUsage",
    "Base",
    "CachedExchangeRate",
    "Category",
    "CategoryRule",
    "Conversation",
    "ConversationMessage",
    "ExportJob",
    "Goal",
    "Household",
    "HouseholdMember",
    "Income",
    "IncomeSource",
    "LineItem",
    "Model",
    "MonthlySnapshot",
    "NameCorrection",
    "PageViewCount",
    "PendingIncome",
    "PlanGrant",
    "PositionMatchOverride",
    "Product",
    "ProductAlias",
    "ProductSelection",
    "Receipt",
    "Recommendation",
    "RefreshToken",
    "RegularExpense",
    "RegularTransfer",
    "TaxPayment",
    "Trip",
    "UploadJob",
    "User",
]

# Registers the flush hook that drops a month's snapshot when one of its receipts
# changes (F6.4). Imported here because every session touching receipts imports
# these models first, whether it is the app's, a test's or the seed script's.
from app.db import snapshot_invalidation  # noqa: F401
