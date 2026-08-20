"""Domain entity mappings.

Import every model module here so `Base.metadata` is complete before Alembic's
`env.py` (autogenerate) or `create_all` (tests) inspect it. Empty until the first
epic (E1+) adds a concrete entity — F0.3 delivers only the base and conventions.
"""

from app.models.base import Base, Model

__all__ = ["Base", "Model"]
