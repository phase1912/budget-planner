import { ThemeStore } from "@/stores/ThemeStore";
import { AuthStore } from "@/stores/AuthStore";
import { ToastStore } from "@/stores/ToastStore";
import { ProfileStore } from "@/stores/ProfileStore";
import { UploadStore } from "@/stores/UploadStore";
import { apiClient } from "@/api/client";

/**
 * Single instantiation point for every MobX store in the client (F9.2.1). Feature
 * epics add their store as a field here; a component or another store never imports
 * a store directly — it reaches every store through this composition, injected via
 * `useStores()`.
 */
export class RootStore {
  readonly themeStore: ThemeStore;
  readonly authStore: AuthStore;
  readonly toastStore: ToastStore;
  readonly profileStore: ProfileStore;
  readonly uploadStore: UploadStore;

  constructor() {
    this.themeStore = new ThemeStore();
    this.toastStore = new ToastStore();
    this.authStore = new AuthStore(apiClient);
    this.profileStore = new ProfileStore(apiClient, this.authStore, this.toastStore);
    this.uploadStore = new UploadStore(apiClient);
  }
}
