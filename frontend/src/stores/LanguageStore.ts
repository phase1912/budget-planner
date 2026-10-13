import { makeAutoObservable, runInAction } from "mobx";

import { apiClient } from "@/api/client";
import { settle } from "@/api/errors";
import i18n from "@/i18n";
import { STORAGE_KEY, isLanguage, type Language } from "@/i18n/languages";
import type { AuthStore } from "@/stores/AuthStore";

/**
 * The language the product is shown in (F9.9). Chosen on this browser before, else the
 * browser's own; once signed in, the account's choice wins, so it follows the user to
 * another device. Choosing one shows it at once, remembers it here and, for a signed-in
 * user, keeps it with the account.
 */
export class LanguageStore {
  language: Language;
  private readonly authStore: AuthStore;
  // The language being saved to the account, so a second ask for it waits on the first.
  private saving: Language | null = null;

  constructor(authStore: AuthStore) {
    this.authStore = authStore;
    this.language = isLanguage(i18n.language) ? i18n.language : "en";
    makeAutoObservable<this, "authStore" | "saving">(
      this,
      { authStore: false, saving: false },
      { autoBind: true },
    );
    this.show(this.language);
  }

  /** The user picks a language: shown now, and kept with their account if signed in. */
  async choose(language: Language): Promise<void> {
    this.show(language);
    const user = this.authStore.user;
    if (!user || user.language === language || this.saving === language) return;
    this.saving = language;
    const response = await settle(() => apiClient.PATCH("/users/me", { body: { language } }));
    this.saving = null;
    if (response.error) return; // Still shown and remembered here; the account catches up next time.
    runInAction(() => {
      if (this.authStore.user) {
        this.authStore.user = { ...this.authStore.user, language };
        localStorage.setItem("budget_user", JSON.stringify(this.authStore.user));
      }
    });
  }

  /**
   * The signed-in account's language takes over; an account that never chose one is given
   * the language the user is already reading, so their next device opens in it too.
   */
  adoptAccount(language: string | null | undefined): void {
    if (isLanguage(language)) {
      if (language !== this.language) this.show(language);
    } else if (this.authStore.user) {
      void this.choose(this.language);
    }
  }

  private show(language: Language): void {
    this.language = language;
    void i18n.changeLanguage(language);
    try {
      localStorage.setItem(STORAGE_KEY, language);
    } catch {
      // Storage blocked: the choice lasts until the page is closed.
    }
    if (typeof document !== "undefined") document.documentElement.lang = language;
  }
}
