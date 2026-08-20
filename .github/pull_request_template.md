<!--
See CONTRIBUTING.md and docs/planning/working-agreement.md for the full ticket-first
workflow. This template exists to keep BRD-to-commit traceability mechanical (F0.5.4).
-->

## Summary

<!-- What changed and why. Assume the reviewer has the diff and lacks the context. -->

## Issues closed

<!--
One line per issue this PR resolves, using a literal closing keyword — a bare mention
of the number will not close the issue or move its board card. At feature scope, list
every task issue under the feature.
-->

Closes #

## BRD requirements

<!-- Requirement IDs this change satisfies, e.g. B2, N2. Leave as "—" if none apply. -->



## Checklist

- [ ] `make lint`, `make typecheck` and `make test` pass locally
- [ ] `docs/architecture/overview.md` / `domain-model.md` updated if this changes a
      component boundary, data flow or business rule
- [ ] Generated API client (`frontend/src/api/schema.ts`) regenerated if a backend
      route, request or response model changed
