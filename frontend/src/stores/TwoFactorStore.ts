import { makeAutoObservable, runInAction } from "mobx";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/schema";
import { errorMessage, settle } from "@/api/errors";
import i18n from "@/i18n";
import { AsyncState } from "@/stores/AsyncState";
import type { AuthStore } from "@/stores/AuthStore";
import type { ToastStore } from "@/stores/ToastStore";

export type TwoFactorSetup = components["schemas"]["TwoFactorSetupRead"];

/**
 * Two-factor sign-in for the signed-in account (F18.6.1): optional for anyone, required
 * for admins. Setting up shows a QR code, a first code turns it on and returns recovery
 * codes shown once; turning it off needs the password and a code.
 */
export class TwoFactorStore {
  readonly state = new AsyncState();
  setup: TwoFactorSetup | null = null;
  /** Shown once, right after turning it on; gone when the user says they saved them. */
  recoveryCodes: string[] | null = null;
  private readonly api: ApiClient;
  private readonly authStore: AuthStore;
  private readonly toastStore: ToastStore;

  constructor(api: ApiClient, authStore: AuthStore, toastStore: ToastStore) {
    this.api = api;
    this.authStore = authStore;
    this.toastStore = toastStore;
    makeAutoObservable<this, "api" | "authStore" | "toastStore">(
      this,
      { api: false, authStore: false, toastStore: false },
      { autoBind: true },
    );
  }

  get enabled(): boolean {
    return this.authStore.user?.two_factor_enabled === true;
  }

  /** Start setting up: a fresh secret and its QR code, not in force until confirmed. */
  async begin(): Promise<void> {
    this.state.start();
    const response = await settle(() => this.api.POST("/users/me/two-factor/setup"));
    runInAction(() => {
      if (response.error !== undefined) {
        this.state.fail(errorMessage(response.error, i18n.t("messages:twoFactor.failed")));
        return;
      }
      this.setup = response.data;
      this.state.reset();
    });
  }

  /** Turn it on with a code from the app; the session becomes a second-factor one. */
  async confirm(code: string): Promise<boolean> {
    this.state.start();
    const response = await settle(() =>
      this.api.POST("/users/me/two-factor/confirm", { body: { code: code.trim() } }),
    );
    return runInAction(() => {
      if (response.error !== undefined) {
        this.state.fail(errorMessage(response.error, i18n.t("messages:twoFactor.failed")));
        return false;
      }
      const { recovery_codes, access_token, refresh_token } = response.data;
      const user = this.authStore.user;
      if (user) {
        this.authStore.adoptSession(
          { ...user, two_factor_enabled: true },
          access_token,
          refresh_token,
        );
      }
      this.setup = null;
      this.recoveryCodes = recovery_codes;
      this.state.succeed();
      return true;
    });
  }

  /** Turn it off with the password and a current code. */
  async disable(password: string, code: string): Promise<boolean> {
    this.state.start();
    const response = await settle(() =>
      this.api.POST("/users/me/two-factor/disable", {
        body: { password, code: code.trim() },
      }),
    );
    return runInAction(() => {
      if (response.error !== undefined) {
        this.state.fail(errorMessage(response.error, i18n.t("messages:twoFactor.failed")));
        return false;
      }
      const user = this.authStore.user;
      if (user) this.authStore.updateUser({ ...user, two_factor_enabled: false });
      this.state.succeed();
      this.toastStore.showSuccess(i18n.t("messages:twoFactor.off"));
      return true;
    });
  }

  /** Close the setup, or the recovery codes once saved. */
  close(): void {
    this.setup = null;
    this.recoveryCodes = null;
    this.state.reset();
  }
}
