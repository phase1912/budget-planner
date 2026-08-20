import { createContext, useContext, useState, type ReactNode } from "react";

import { RootStore } from "@/stores/RootStore";

const StoreContext = createContext<RootStore | null>(null);

interface StoreProviderProps {
  children: ReactNode;
  /** Test-only escape hatch: inject a stub RootStore instead of constructing a real one. */
  store?: RootStore;
}

/**
 * Instantiates the single RootStore for the app and provides it through context
 * (F9.2.1). Mounted once, above the router, in main.tsx.
 */
export function StoreProvider({ children, store }: StoreProviderProps) {
  const [rootStore] = useState(() => store ?? new RootStore());
  return <StoreContext.Provider value={rootStore}>{children}</StoreContext.Provider>;
}

/**
 * The only way a component reaches store state (F9.2.1). Throws outside a
 * StoreProvider rather than silently returning undefined, so a missing provider
 * fails at the call site instead of surfacing as a confusing render bug.
 */
export function useStores(): RootStore {
  const store = useContext(StoreContext);
  if (!store) {
    throw new Error("useStores must be used within a StoreProvider");
  }
  return store;
}
