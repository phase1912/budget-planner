# backend

The FastAPI service. Owns all business logic and is the only thing that talks to
PostgreSQL, object storage or the Claude API.

Nothing here imports from `frontend/`. See [the architecture overview](../docs/architecture/overview.md#repository-layout-and-the-frontendbackend-boundary)
for the layering (router → service → repository → port) and the import boundary rule.

Not yet scaffolded — tracked by [F0.2](../docs/planning/backlog.yaml) (application
skeleton) and [F0.3](../docs/planning/backlog.yaml) (PostgreSQL/SQLAlchemy/Alembic).
