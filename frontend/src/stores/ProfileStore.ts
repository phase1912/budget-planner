import { makeAutoObservable, runInAction } from "mobx";
import type { ApiClient } from "@/api/client";
import type { components } from "@/api/schema";
import { AsyncState } from "@/stores/AsyncState";
import type { AuthStore } from "@/stores/AuthStore";
import type { ToastStore } from "@/stores/ToastStore";

export type UserUpdateRequest = components["schemas"]["UserUpdateRequest"];

export class ProfileStore {
  readonly updateState = new AsyncState();
  private readonly api: ApiClient;
  private readonly authStore: AuthStore;
  private readonly toastStore: ToastStore;

  constructor(api: ApiClient, authStore: AuthStore, toastStore: ToastStore) {
    this.api = api;
    this.authStore = authStore;
    this.toastStore = toastStore;
    makeAutoObservable(this);
  }

  /**
   * Re-read the signed-in user, so fields added since the session began (the forwarding
   * address, F11.2) appear without signing in again. On failure, keep what was known.
   */
  async loadProfile(): Promise<void> {
    try {
      const { data } = await this.api.GET("/users/me");
      if (!data) return;
      runInAction(() => {
        if (this.authStore.user) {
          this.authStore.user = { ...this.authStore.user, ...data };
          localStorage.setItem("budget_user", JSON.stringify(this.authStore.user));
        }
      });
    } catch {
      // Offline or signed out: the cached profile is still right for everything else.
    }
  }

  async updateProfile(request: UserUpdateRequest): Promise<boolean> {
    this.updateState.start();
    try {
      const { data, error } = await this.api.PATCH("/users/me", {
        body: request,
      });

      // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
      if (error || !data) {
        const detail = (error as { detail?: string }).detail ?? "Failed to update profile";
        this.updateState.fail(detail);
        this.toastStore.showError(detail);
        return false;
      }

      runInAction(() => {
        // Synchronize updated user back to AuthStore
        if (this.authStore.user) {
          this.authStore.user = {
            ...this.authStore.user,
            ...data,
          };
          localStorage.setItem("budget_user", JSON.stringify(this.authStore.user));
        }
      });
      this.updateState.succeed();
      this.toastStore.showSuccess("Profile updated successfully");
      return true;
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : "Unknown error";
      this.updateState.fail(errMsg);
      this.toastStore.showError(errMsg);
      return false;
    }
  }

  readonly regenerateState = new AsyncState();

  /** Replace the receipt forwarding address; the old one stops working (F11.2). */
  async regenerateForwardingAddress(): Promise<boolean> {
    this.regenerateState.start();
    try {
      const { data, error } = await this.api.POST("/users/me/forwarding-address/regenerate");

      // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
      if (error || !data) {
        const detail = (error as { detail?: string }).detail ?? "Failed to regenerate address";
        this.regenerateState.fail(detail);
        this.toastStore.showError(detail);
        return false;
      }

      runInAction(() => {
        if (this.authStore.user) {
          this.authStore.user = {
            ...this.authStore.user,
            ...data,
          };
          localStorage.setItem("budget_user", JSON.stringify(this.authStore.user));
        }
      });
      this.regenerateState.succeed();
      this.toastStore.showSuccess("New forwarding address ready");
      return true;
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : "Unknown error";
      this.regenerateState.fail(errMsg);
      this.toastStore.showError(errMsg);
      return false;
    }
  }
}
