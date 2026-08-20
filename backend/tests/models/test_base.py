"""Tests for the declarative base and shared model conventions (F0.3.3).

Assertions run against compiled DDL for the postgresql dialect rather than a
live connection — constraint naming and column typing are static properties
of the mapping, not something that needs a database to observe. The migration
these conventions depend on (`gen_random_uuid()` needing PostgreSQL 13+, which
ships it without pgcrypto) is verified against a real database in
tests/db/test_baseline_migration.py.
"""

from collections.abc import Iterator

import pytest
from sqlalchemy import String
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import CreateTable

from app.models.base import Base, Model


class _ConventionsProbe(Model):
    """A throwaway mapped class used only to inspect `Model`'s generated DDL."""

    __tablename__ = "test_conventions_probe"

    name: Mapped[str] = mapped_column(String(100), unique=True)


_probe_table = Base.metadata.tables["test_conventions_probe"]


@pytest.fixture(autouse=True)
def _drop_probe_table_after_test() -> Iterator[None]:
    """Keep the probe table out of Base.metadata once this module is done with it.

    Otherwise it would sit alongside real domain tables for the rest of the
    pytest session, since Model shares one process-wide registry with every
    other entity that extends it.
    """
    yield
    Base.metadata.remove(_probe_table)


def _compiled_ddl() -> str:
    # postgresql.dialect() has no type stub upstream (SQLAlchemy).
    dialect = postgresql.dialect()  # type: ignore[no-untyped-call]
    return str(CreateTable(_probe_table).compile(dialect=dialect))


def test_primary_key_is_a_uuid_generated_by_the_database() -> None:
    assert "id UUID DEFAULT gen_random_uuid() NOT NULL" in _compiled_ddl()


def test_created_at_and_updated_at_are_timezone_aware_with_server_defaults() -> None:
    ddl = _compiled_ddl()
    assert "created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL" in ddl
    assert "updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL" in ddl


def test_updated_at_reassigns_on_every_orm_issued_update() -> None:
    assert _probe_table.c.updated_at.onupdate is not None


def test_constraint_names_follow_the_naming_convention() -> None:
    ddl = _compiled_ddl()
    assert "CONSTRAINT pk_test_conventions_probe PRIMARY KEY (id)" in ddl
    assert "CONSTRAINT uq_test_conventions_probe_name UNIQUE (name)" in ddl
