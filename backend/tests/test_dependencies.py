"""Smoke tests for the backend's pinned runtime dependencies (F0.1.2).

These do not test business behaviour — there is none yet. They guard the one thing
this task actually delivers: that the packages the project depends on are installed,
importable, and resolved to the major versions the ADR (0001-technology-stack) and the
backlog task require.
"""

import importlib

import sqlalchemy


def test_all_pinned_runtime_dependencies_are_importable() -> None:
    """Every package pinned in pyproject.toml's [project.dependencies] must import.

    A dependency that resolves but fails to import (e.g. a broken wheel, a missing
    native extension) would otherwise only surface once application code exercises it.
    """
    for module_name in ("fastapi", "sqlalchemy", "alembic", "pydantic_settings", "anthropic"):
        importlib.import_module(module_name)


def test_sqlalchemy_is_pinned_to_the_2x_major_version() -> None:
    """ADR-0001 specifies SQLAlchemy 2.x; a resolve onto 1.x or 3.x is a regression."""
    assert sqlalchemy.__version__.startswith("2.")
