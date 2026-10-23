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
npm run typecheck      # type check only (tsc -b, no emit)
npm run lint          # eslint
npm run format         # prettier --check
npm run test          # vitest run
npm run generate:api   # regenerate src/api/schema.ts from the backend's OpenAPI schema
```

Regenerate `src/api/schema.ts` after any backend route or model change and commit the
result — CI fails the build if the checked-in file is stale (F9.3.3). Requires the
backend's `uv` environment (`cd backend && uv sync`) to be set up locally.

The repo-root `Makefile` runs this alongside the backend's equivalent commands
(`make test`, `make lint`, `make typecheck`, F0.4.2) — use those when a change touches
both sides.

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

**Stores**: a single `RootStore`, provided via React context and read with
`useStores()` — see [`src/stores/README.md`](src/stores/README.md) for the
composition rule, the observable-vs-derived rule, and the async-action
convention every store follows (F9.2).

**shared/ vs feature-local**: a component or style belongs in `shared/` only if it is
used by more than one feature _and_ carries no feature-specific business logic.
Everything else lives under `components/<feature>/`. When in doubt, start local — moving
something into `shared/` later is cheap; pulling business logic back out of a shared
component that accreted it is not.

Import path alias: `@/` resolves to `src/` (configured in both `tsconfig.app.json` and
`vite.config.ts` — see F9.1.1).

## The store apps (Capacitor)

The Android and iOS apps are this build served from the device (ADR-0033).

**iOS, from Xcode.** Open `ios/App/App.xcodeproj`, pick a scheme and press Run — the client
is built as a step of the app's own build, so the app never carries a stale one:

- **App (Local)** builds against the API on this Mac (`http://localhost:8000`): for
  backend changes not yet deployed, on the simulator, which reaches the Mac as `localhost`.
- **App (Production)** builds against the production API: for a phone, and for trying the
  app as a user would. Archives for the App Store use it too.

A failed client build fails the app's. The step (`ios/App/build-web.sh`) finds Node through
nvm or Homebrew, as the terminal does.

**From the terminal** (in `frontend/`), for Android or without Xcode: `npm run app:prod` or
`npm run app:local` builds the client and copies it into both native projects; then open
`android/` in Android Studio. Both APIs allow the apps' origins. The production address is
the Cloud Run service's own; if the service is ever recreated under another one, change it in
`package.json`.
