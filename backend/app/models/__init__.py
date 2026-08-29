"""Domain entity mappings.

Import every model module here so `Base.metadata` is complete before Alembic's
`env.py` (autogenerate) or `create_all` (tests) inspect it. Empty until the first
epic (E1+) adds a concrete entity — F0.3 delivers only the base and conventions.
"""

from app.models.base import Base, Model
from app.models.category import Category
from app.models.line_item import LineItem
from app.models.receipt import Receipt
from app.models.refresh_token import RefreshToken
from app.models.upload_job import UploadJob
from app.models.user import User

__all__ = [
    "Base",
    "Category",
    "LineItem",
    "Model",
    "Receipt",
    "RefreshToken",
    "UploadJob",
    "User",
]
