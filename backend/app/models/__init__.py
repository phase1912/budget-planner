"""Domain entity mappings.

Import every model module here so `Base.metadata` is complete before Alembic's
`env.py` (autogenerate) or `create_all` (tests) inspect it. Empty until the first
epic (E1+) adds a concrete entity — F0.3 delivers only the base and conventions.
"""

from app.models.base import Base, Model
from app.models.category import Category
from app.models.category_rule import CategoryRule
from app.models.line_item import LineItem
from app.models.match_override import PositionMatchOverride
from app.models.monthly_snapshot import MonthlySnapshot
from app.models.receipt import Receipt
from app.models.refresh_token import RefreshToken
from app.models.upload_job import UploadJob
from app.models.user import User

__all__ = [
    "Base",
    "Category",
    "CategoryRule",
    "LineItem",
    "Model",
    "MonthlySnapshot",
    "PositionMatchOverride",
    "Receipt",
    "RefreshToken",
    "UploadJob",
    "User",
]

# Registers the flush hook that drops a month's snapshot when one of its receipts
# changes (F6.4). Imported here because every session touching receipts imports
# these models first, whether it is the app's, a test's or the seed script's.
from app.db import snapshot_invalidation  # noqa: F401
