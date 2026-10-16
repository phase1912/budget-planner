import { makeAutoObservable, runInAction } from "mobx";

import type { ApiClient } from "@/api/client";
import { errorMessage, settle } from "@/api/errors";
import i18n from "@/i18n";
import { screenLanguage } from "@/i18n/languages";
import { AsyncState } from "@/stores/AsyncState";
import type { AuthStore, User } from "@/stores/AuthStore";
import type { ToastStore } from "@/stores/ToastStore";

/**
 * An account's address and password, changed through links sent by email (F17.8):
 * confirming the address, resending that link, a forgotten password, a new address.
 * One action runs at a time, so one `state` serves whichever screen is open; a screen
 * resets it when it opens.
 */
export class AccountStore {
  readonly state = new AsyncState();
  /** The address a followed link confirmed, to name it on the screen that followed it. */
  confirmedEmail: string | null = null;
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

  /** Whether the signed-in account still has to confirm its address (F17.8.2). */
  get mustConfirm(): boolean {
    // A session from before F17.8 has no flag stored: its account was confirmed by the migration.
    return this.authStore.user?.email_confirmed === false;
  }

  reset(): void {
    this.state.reset();
    this.confirmedEmail = null;
  }

  /** Follow a confirmation link; the signed-in user, if it is them, is updated in place. */
  async confirmEmail(token: string): Promise<void> {
    await this.run(
      () => this.api.POST("/auth/confirm-email", { body: { token } }),
      (user) => {
        this.adopt(user);
      },
    );
  }

  /** Send the confirmation link again (F17.8.2). */
  async resendConfirmation(): Promise<void> {
    const sent = await this.run(() => this.api.POST("/users/me/confirmation/resend"));
    if (sent) this.toastStore.showSuccess(i18n.t("messages:account.linkSent"));
  }

  /** Ask for a reset link; the answer is the same whether the address has an account. */
  async forgotPassword(email: string): Promise<void> {
    await this.run(() =>
      this.api.POST("/auth/password/forgot", {
        body: { email, language: screenLanguage(i18n.language) },
      }),
    );
  }

  /** Set a new password from a reset link; every session ends, this one included. */
  async resetPassword(token: string, password: string): Promise<void> {
    const done = await this.run(() =>
      this.api.POST("/auth/password/reset", { body: { token, password } }),
    );
    if (done) this.authStore.logoutLocally();
  }

  /** Ask to move the account to another address: a link goes to it (F17.8.3). */
  async changeEmail(email: string, password: string): Promise<boolean> {
    return this.run(() => this.api.POST("/users/me/email", { body: { email, password } }));
  }

  /** Follow the link sent to a new address: the account switches to it. */
  async confirmEmailChange(token: string): Promise<void> {
    await this.run(
      () => this.api.POST("/auth/email/confirm-change", { body: { token } }),
      (user) => {
        this.adopt(user);
      },
    );
  }

  /** Delete the account and everything held about its owner (F17.9.1); signs out here. */
  async deleteAccount(password: string): Promise<boolean> {
    const done = await this.run(() => this.api.DELETE("/users/me", { body: { password } }));
    if (done) {
      this.authStore.logoutLocally();
      this.toastStore.showSuccess(i18n.t("messages:account.deleted"));
    }
    return done;
  }

  private adopt(user: User): void {
    this.confirmedEmail = user.email;
    if (this.authStore.user?.id !== user.id) return;
    this.authStore.user = { ...this.authStore.user, ...user };
    localStorage.setItem("budget_user", JSON.stringify(this.authStore.user));
  }

  private async run<T>(
    send: () => Promise<{ data?: T; error?: unknown }>,
    onData?: (data: T) => void,
  ): Promise<boolean> {
    this.state.start();
    const response = await settle(send);
    runInAction(() => {
      if (response.error !== undefined) {
        this.state.fail(errorMessage(response.error, i18n.t("messages:account.failed")));
        return;
      }
      if (onData && response.data !== undefined) onData(response.data);
      this.state.succeed();
    });
    return response.error === undefined;
  }
}
