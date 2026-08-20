# ADR-0003 — Test data factories: polyfactory over factory_boy

- **Status:** Accepted
- **Date:** 2026-08-20

## Context

F0.6.3 needs a base class and naming convention for building test data, so a BDD
scenario's `Given` steps can read as business language ("Given a receipt with 3 line
items") rather than hand-assembled ORM setup. Every future domain-entity task builds
its factory on top of whatever this ADR fixes, so the choice is not free to revisit
per entity.

`factory_boy` is the more established library for this in the Python ecosystem, and
its `SQLAlchemyModelFactory` is the usual default. But this codebase's database access
is async-only (F0.3.1, `AsyncSession` throughout) — `factory_boy`'s SQLAlchemy support
assumes a synchronous `Session`, which would mean either running factories through a
sync session that does not participate in the same transaction as the rest of a test,
or writing and maintaining our own async persistence shim on top of it.

`polyfactory` ships `polyfactory.factories.sqlalchemy_factory.SQLAlchemyFactory` with
native support for both a sync `Session` and an async `AsyncSession` — `create_async()`
persists through whichever `AsyncSession` is bound to the factory, so a factory-built
row lands in exactly the same transaction `db_session` (F0.6.1) is managing for a test.
It also derives field types and constraints directly from the SQLAlchemy mapping, so an
entity factory rarely needs to hand-write a default per column.

## Decision

Test entity factories are built on `polyfactory`, not `factory_boy`.

`backend/tests/factories/base.py` defines `ModelFactory`, the base every entity factory
extends. The convention: one file per entity, `tests/factories/<entity_snake_case>.py`,
exposing a single `<Entity>Factory(ModelFactory[<Entity>])` with `__model__` set.
`tests/conftest.py`'s `db_session` fixture binds `ModelFactory.__async_session__` to the
current test's session for the fixture's lifetime, so a concrete factory's
`create_async()` needs no session argument and is rolled back with everything else that
session touched.

No per-entity factory is delivered by F0.6.3 itself — no domain entity exists yet at E0.
Each is added by the epic that introduces that entity, the same rule F1.3's cross-user
test suite follows.

## Consequences

- Adding a new entity factory means subclassing `ModelFactory`, not learning a second
  library's API — the async persistence wiring is already solved once, in the base
  class and `db_session`.
- `polyfactory` is a smaller, newer project than `factory_boy`; if its SQLAlchemy
  support regresses or the project stalls, migrating every entity factory written
  against `ModelFactory` is real work concentrated in one place (`tests/factories/`),
  not scattered per-test setup — this is the trade this ADR accepts in exchange for
  today's simpler async story.
