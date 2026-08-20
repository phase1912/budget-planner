# Store conventions

How MobX state is composed and consumed in this client, and the two rules every
store follows. Read this once; the pattern repeats identically in every feature
epic that adds a store.

## Root store and dependency injection (F9.2.1)

There is exactly one `RootStore` (`RootStore.ts`), instantiated once by
`StoreProvider` and provided through React context. Components read it with the
`useStores()` hook:

```tsx
function ThemeToggle() {
  const { themeStore } = useStores();
  return <button onClick={() => themeStore.toggleTheme()}>{themeStore.theme}</button>;
}
```

Rules this enforces:

- **No direct imports between stores.** A store that needs another store's state
  receives the whole `RootStore` (or the specific store) through its constructor,
  the same way a backend service receives a port via `Depends` — see the DIP
  section of the root `CLAUDE.md`. Reaching for `import { otherStore } from
"@/stores/OtherStore"` inside a store file is the smell to catch in review.
- **No component reaches into a store via anything but `useStores()`.** Not a
  singleton import, not prop-drilling a store instance from `App`.
- **Tests inject a stub `RootStore`** via `<StoreProvider store={testStore}>`
  rather than mounting the real one, so a component test never depends on
  `ThemeStore` reading `localStorage` or a real `matchMedia`.

## Observable vs. derived

- A field is `observable` when it is the source of truth — something only an
  action changes, nothing computes it from other state. `ThemeStore.theme` is
  observable: it is set directly by `setTheme`, not derived from anything else.
- A field is a computed `get` when its value is always recomputable from other
  observable state. Never store a derived value as its own observable and keep it
  in sync by hand — that duplication is exactly what MobX's `computed` exists to
  eliminate. `AsyncState.isLoading` is the example: it is `status === "loading"`,
  never a separate observable flag that could drift from `status`.

`makeAutoObservable(this)` in a store's constructor infers this automatically
(fields become `observable`, getters become `computed`, methods become
`action`) — no store needs to hand-write MobX annotations.

## Async action status (F9.2.2)

Every store action that involves a promise (an API call, in particular — F9.3)
reports its progress the same way: an `idle` → `loading` → `success` | `error`
status, not a bespoke `isFetching`/`hasFailed` pair of booleans invented per
store. `AsyncState.ts` is that shape, ready to compose into a store:

```ts
class ReceiptStore {
  receipts: Receipt[] = [];
  readonly loadState = new AsyncState();

  constructor(private readonly api: ReceiptsApi) {
    makeAutoObservable(this);
  }

  async load(): Promise<void> {
    this.loadState.start();
    try {
      this.receipts = await this.api.list();
      this.loadState.succeed();
    } catch (error) {
      this.loadState.fail(error instanceof Error ? error.message : "Unknown error");
    }
  }
}
```

A component reads `store.loadState.status` (or the `isLoading` computed) to
decide what to render — never a `try`/`catch` or a `.then()` inside the
component itself. Fetching is the store's job; rendering the result is the
component's.
