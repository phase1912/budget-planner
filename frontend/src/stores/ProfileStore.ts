import { makeAutoObservable, runInAction } from "mobx";
import type { ApiClient } from "@/api/client";
import type { components } from "@/api/schema";
import { AsyncState } from "@/stores/AsyncState";
import type { AuthStore } from "@/stores/AuthStore";
import type { ToastStore } from "@/stores/ToastStore";
import type { Palette, ThemeStore } from "@/stores/ThemeStore";
import i18n from "@/i18n";
import { errorMessage } from "@/api/errors";

export type UserUpdateRequest = components["schemas"]["UserUpdateRequest"];

export class ProfileStore {
  readonly updateState = new AsyncState();
  private readonly api: ApiClient;
  private readonly authStore: AuthStore;
  private readonly toastStore: ToastStore;
  private readonly themeStore: ThemeStore | null;

  constructor(
    api: ApiClient,
    authStore: AuthStore,
    toastStore: ToastStore,
    themeStore: ThemeStore | null = null,
  ) {
    this.api = api;
    this.authStore = authStore;
    this.toastStore = toastStore;
    this.themeStore = themeStore;
    makeAutoObservable(this);
  }

  /** Paint the palette at once and keep it on the account for other devices (F23.1). */
  async choosePalette(palette: Palette): Promise<void> {
    this.themeStore?.setPalette(palette);
    await this.saveQuietly({ palette });
  }

  /** Midnight whenever the device is dark, here and on the account. */
  async chooseDarkAtNight(on: boolean): Promise<void> {
    this.themeStore?.setDarkAtNight(on);
    await this.saveQuietly({ dark_at_night: on });
  }

  /**
   * Finish the first sign-in (F23.9): what was chosen, and that it is done, so it does not
   * come back on another device. A currency the account can no longer change — it has
   * receipts already — is left as it is rather than failing the rest.
   */
  async finishOnboarding(request: UserUpdateRequest): Promise<boolean> {
    const body = { ...request, onboarded: true };
    const first = await this.api.PATCH("/users/me", { body });
    const locked = (first.error as { code?: string } | undefined)?.code === "currency_locked";
    const response = locked
      ? await this.api.PATCH("/users/me", { body: { ...body, currency: undefined } })
      : first;
    if (response.error !== undefined) {
      this.toastStore.showError(
        errorMessage(response.error, i18n.t("messages:profile.updateFailed")),
      );
      return false;
    }
    runInAction(() => {
      this.adoptUser(response.data);
    });
    return true;
  }

  /**
   * Save one setting without a toast — a switch that moves is its own confirmation. A
   * failure is told, and the account keeps what it had.
   */
  /**
   * Allow the AI to read the account's receipts, words and recordings, or withdraw that
   * (F25.3.2); until it is allowed, every AI feature waits. Asked of the user, never assumed.
   */
  async setAiConsent(given: boolean): Promise<boolean> {
    try {
      const { data, error } = await this.api.PUT("/users/me/ai-consent", { body: { given } });
      if (error !== undefined) {
        this.toastStore.showError(errorMessage(error, i18n.t("messages:profile.updateFailed")));
        return false;
      }
      runInAction(() => {
        this.adoptUser(data);
      });
      return true;
    } catch {
      this.toastStore.showError(i18n.t("messages:profile.updateFailed"));
      return false;
    }
  }

  async saveQuietly(request: UserUpdateRequest): Promise<boolean> {
    try {
      const { data, error } = await this.api.PATCH("/users/me", { body: request });
      // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
      if (error || !data) {
        this.toastStore.showError(errorMessage(error, i18n.t("messages:profile.updateFailed")));
        return false;
      }
      runInAction(() => {
        this.adoptUser(data);
      });
      return true;
    } catch {
      this.toastStore.showError(i18n.t("messages:profile.updateFailed"));
      return false;
    }
  }

  private adoptUser(data: Partial<NonNullable<AuthStore["user"]>>): void {
    if (!this.authStore.user) return;
    this.authStore.user = { ...this.authStore.user, ...data };
    localStorage.setItem("budget_user", JSON.stringify(this.authStore.user));
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
        const detail = errorMessage(error, i18n.t("messages:profile.updateFailed"));
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
      this.toastStore.showSuccess(i18n.t("messages:profile.updated"));
      return true;
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : i18n.t("messages:unknown");
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
        const detail = errorMessage(error, i18n.t("messages:profile.addressFailed"));
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
      this.toastStore.showSuccess(i18n.t("messages:profile.addressReady"));
      return true;
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : i18n.t("messages:unknown");
      this.regenerateState.fail(errMsg);
      this.toastStore.showError(errMsg);
      return false;
    }
  }
}
