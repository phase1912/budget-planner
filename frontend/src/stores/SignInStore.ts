import { makeAutoObservable, runInAction } from "mobx";

import type { ApiClient } from "@/api/client";
import { API_BASE_URL } from "@/api/baseUrl";
import type { components } from "@/api/schema";
import { errorMessage } from "@/api/errors";
import i18n from "@/i18n";
import type { AuthStore } from "@/stores/AuthStore";
import type { ToastStore } from "@/stores/ToastStore";

export type SignInProvider = "google" | "apple";
export type LinkedIdentity = components["schemas"]["LinkedIdentityRead"];
type ProviderSignInRequest = components["schemas"]["ProviderSignInRequest"];

/** The sign-in under way, kept for the trip to the provider and back only. */
const ATTEMPT_KEY = "budget_sign_in_attempt";

interface Attempt {
  provider: SignInProvider;
  nonce: string;
  state: string;
  /** "link" when started from Settings by a signed-in user. */
  mode: "sign-in" | "link";
}

/** What the callback screen waits for after the provider has answered. */
export type Finish = "signed-in" | "second-factor" | "needs-terms" | "needs-password" | "failed";

function randomToken(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(24));
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

/** Where each provider's own sign-in page is, with what it is asked for. */
function providerUrl(provider: SignInProvider, clientId: string, attempt: Attempt): string {
  if (provider === "google") {
    const query = new URLSearchParams({
      client_id: clientId,
      redirect_uri: `${window.location.origin}/auth/callback/google`,
      response_type: "id_token",
      scope: "openid email profile",
      nonce: attempt.nonce,
      state: attempt.state,
      prompt: "select_account",
    });
    return `https://accounts.google.com/o/oauth2/v2/auth?${query.toString()}`;
  }
  // Apple posts its answer to the server, which hands it back here (F1.6.2).
  const query = new URLSearchParams({
    client_id: clientId,
    redirect_uri: `${API_BASE_URL}/auth/apple/callback`,
    response_type: "code id_token",
    response_mode: "form_post",
    scope: "name email",
    nonce: attempt.nonce,
    state: attempt.state,
  });
  return `https://appleid.apple.com/auth/authorize?${query.toString()}`;
}

/**
 * Signing in with Google and Apple on the website (F1.6.2): which providers are on, the
 * trip to the provider's page and back, and the providers linked in Settings.
 *
 * Nothing is loaded from the providers into the page: the browser goes to their sign-in
 * page and comes back with the ID token in the address's fragment, which no server
 * sees. A `state` kept for the trip proves the answer belongs to this sign-in. The store
 * apps do not offer it yet — Google refuses sign-in inside an app's web view, and the
 * native sign-ins wait for the providers' keys.
 */
export class SignInStore {
  clientIds: Record<SignInProvider, string | null> = { google: null, apple: null };
  identities: LinkedIdentity[] = [];
  error: string | null = null;
  isWorking = false;
  /** Where the sign-in that came back was started: Settings links, the sign-in page signs in. */
  mode: Attempt["mode"] = "sign-in";
  private pending: { provider: SignInProvider; request: ProviderSignInRequest } | null = null;
  private readonly api: ApiClient;
  private readonly authStore: AuthStore;
  private readonly toastStore: ToastStore;

  constructor(api: ApiClient, authStore: AuthStore, toastStore: ToastStore) {
    this.api = api;
    this.authStore = authStore;
    this.toastStore = toastStore;
    makeAutoObservable<SignInStore, "api" | "authStore" | "toastStore">(this, {
      api: false,
      authStore: false,
      toastStore: false,
    });
  }

  /** The providers switched on, in the order their buttons show. */
  get available(): SignInProvider[] {
    return (["google", "apple"] as const).filter((p) => this.clientIds[p] !== null);
  }

  async loadProviders(): Promise<void> {
    try {
      const { data } = await this.api.GET("/auth/providers");
      if (data) {
        runInAction(() => {
          this.clientIds = { google: data.google ?? null, apple: data.apple ?? null };
        });
      }
    } catch {
      // Offline or asleep: the buttons simply stay hidden, the password still works.
    }
  }

  /** Leave for the provider's sign-in page; `link` adds it to the signed-in account. */
  start(provider: SignInProvider, mode: Attempt["mode"] = "sign-in"): void {
    const clientId = this.clientIds[provider];
    if (clientId === null) return;
    const attempt: Attempt = { provider, nonce: randomToken(), state: randomToken(), mode };
    sessionStorage.setItem(ATTEMPT_KEY, JSON.stringify(attempt));
    window.location.assign(providerUrl(provider, clientId, attempt));
  }

  /**
   * Take the provider's answer from the address's fragment and sign in with it.
   * A different `state`, a cancelled sign-in or a token the server refuses ends in
   * "failed" with `error` set; a new account asks for the terms, an existing address
   * for its password, each answered through `answer`.
   */
  async finish(provider: SignInProvider, fragment: string): Promise<Finish> {
    const fields = new URLSearchParams(fragment.replace(/^#/, ""));
    const saved = sessionStorage.getItem(ATTEMPT_KEY);
    sessionStorage.removeItem(ATTEMPT_KEY);
    const attempt = saved ? (JSON.parse(saved) as Attempt) : null;
    const idToken = fields.get("id_token");
    if (
      attempt?.provider !== provider ||
      attempt.state !== fields.get("state") ||
      idToken === null
    ) {
      runInAction(() => {
        this.error = i18n.t("auth:providers.cancelled");
      });
      return "failed";
    }
    runInAction(() => {
      this.mode = attempt.mode;
    });
    this.pending = {
      provider,
      request: {
        id_token: idToken,
        nonce: attempt.nonce,
        accept_terms: false,
        first_name: fields.get("first_name") ?? null,
        last_name: fields.get("last_name") ?? null,
        authorization_code: fields.get("code"),
      },
    };
    return this.send();
  }

  /** Send the waiting sign-in again with the terms accepted, or the account's password. */
  async answer(extra: { accept_terms?: boolean; password?: string }): Promise<Finish> {
    if (this.pending === null) return "failed";
    this.pending.request = { ...this.pending.request, ...extra };
    return this.send();
  }

  private async send(): Promise<Finish> {
    const pending = this.pending;
    if (pending === null) return "failed";
    this.isWorking = true;
    this.error = null;
    try {
      const { data, error } = await this.api.POST("/auth/oidc/{provider}", {
        params: { path: { provider: pending.provider } },
        body: pending.request,
      });
      const code = (error as { code?: string } | undefined)?.code;
      return runInAction((): Finish => {
        this.isWorking = false;
        if (code === "terms_required") return "needs-terms";
        if (code === "link_needs_password") return "needs-password";
        if (error !== undefined || data === undefined) {
          this.error = errorMessage(error, i18n.t("messages:auth.failed"));
          return "failed";
        }
        this.pending = null;
        if ("second_factor_token" in data) {
          this.authStore.secondFactorToken = data.second_factor_token;
          return "second-factor";
        }
        this.authStore.adoptSession(data.user, data.access_token, data.refresh_token);
        return "signed-in";
      });
    } catch {
      runInAction(() => {
        this.isWorking = false;
        this.error = i18n.t("messages:auth.failed");
      });
      return "failed";
    }
  }

  async loadIdentities(): Promise<void> {
    try {
      const { data } = await this.api.GET("/users/me/identities");
      if (data) {
        runInAction(() => {
          this.identities = data;
        });
      }
    } catch {
      // The list stays as it was; Settings still shows what it has.
    }
  }

  /** Stop a provider signing in; refused while it is the account's only way in. */
  async unlink(provider: SignInProvider): Promise<boolean> {
    try {
      const { error } = await this.api.DELETE("/users/me/identities/{provider}", {
        params: { path: { provider } },
      });
      if (error !== undefined) {
        this.toastStore.showError(errorMessage(error, i18n.t("messages:profile.updateFailed")));
        return false;
      }
      runInAction(() => {
        this.identities = this.identities.filter((i) => i.provider !== provider);
      });
      this.toastStore.showSuccess(i18n.t("messages:profile.providerUnlinked"));
      return true;
    } catch {
      this.toastStore.showError(i18n.t("messages:profile.updateFailed"));
      return false;
    }
  }
}
