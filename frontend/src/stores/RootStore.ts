import { reaction } from "mobx";

import { ThemeStore } from "@/stores/ThemeStore";
import { AuthStore } from "@/stores/AuthStore";
import { ToastStore } from "@/stores/ToastStore";
import { ProfileStore } from "@/stores/ProfileStore";
import { UploadStore } from "@/stores/UploadStore";
import { apiClient } from "@/api/client";

import { CategoriesStore } from "@/stores/CategoriesStore";
import { ReceiptStore } from "@/stores/ReceiptStore";
import { BudgetStore } from "@/stores/BudgetStore";

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
  readonly receiptStore: ReceiptStore;
  readonly categoriesStore: CategoriesStore;
  readonly budgetStore: BudgetStore;

  constructor() {
    this.themeStore = new ThemeStore();
    this.toastStore = new ToastStore();
    this.authStore = new AuthStore(apiClient);
    this.profileStore = new ProfileStore(apiClient, this.authStore, this.toastStore);
    this.budgetStore = new BudgetStore();
    // Any receipt change may have recalculated the month on screen (BRD D6, F6.5).
    const refreshMonth = () => void this.budgetStore.refresh();
    this.uploadStore = new UploadStore(apiClient, this.toastStore, refreshMonth);
    this.receiptStore = new ReceiptStore(this.toastStore, refreshMonth);
    this.categoriesStore = new CategoriesStore();
    // The month view remembers where it was left; a new account starts afresh.
    reaction(
      () => this.authStore.user?.id,
      () => {
        this.budgetStore.reset();
      },
    );
  }
}
