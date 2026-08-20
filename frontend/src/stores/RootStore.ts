import { ThemeStore } from "@/stores/ThemeStore";

/**
 * Single instantiation point for every MobX store in the client (F9.2.1). Feature
 * epics add their store as a field here; a component or another store never imports
 * a store directly — it reaches every store through this composition, injected via
 * `useStores()`.
 */
export class RootStore {
  readonly themeStore: ThemeStore;

  constructor() {
    this.themeStore = new ThemeStore();
  }
}
