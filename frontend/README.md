# frontend

The React + MobX client, scaffolded with Vite and strict TypeScript (F9.1).

The only way this talks to `backend/` is through the generated OpenAPI client — never
a hand-written fetch call, never an import that reaches into the backend source tree.
See [the architecture overview](../docs/architecture/overview.md#repository-layout-and-the-frontendbackend-boundary)
for why.

## Commands

```
npm install
npm run dev          # start the Vite dev server
npm run build         # type check (tsc -b) then production build
npm run lint          # eslint
npm run format         # prettier --check
npm run test          # vitest run
```

## Structure

```
src/
  pages/               Route-level components, one per screen
  components/           Feature-scoped components, grouped by feature
  shared/
    components/         Components used by more than one feature, with no
                         feature-specific business logic
    styles/              Design tokens and global styles
  stores/                MobX stores — state and the actions that change it
  api/                   The generated OpenAPI client (F9.3) and its wrappers
  routes/                Route definitions
```

**shared/ vs feature-local**: a component or style belongs in `shared/` only if it is
used by more than one feature _and_ carries no feature-specific business logic.
Everything else lives under `components/<feature>/`. When in doubt, start local — moving
something into `shared/` later is cheap; pulling business logic back out of a shared
component that accreted it is not.

Import path alias: `@/` resolves to `src/` (configured in both `tsconfig.app.json` and
`vite.config.ts` — see F9.1.1).
