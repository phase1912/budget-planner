# frontend

The React + MobX client.

The only way this talks to `backend/` is through the generated OpenAPI client — never
a hand-written fetch call, never an import that reaches into the backend source tree.
See [the architecture overview](../docs/architecture/overview.md#repository-layout-and-the-frontendbackend-boundary)
for why.

Not yet scaffolded — tracked by [F9.1](../docs/planning/backlog.yaml) (project setup)
through [F9.7](../docs/planning/backlog.yaml) (state conventions).
