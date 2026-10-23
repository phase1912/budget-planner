import { makeAutoObservable, runInAction } from "mobx";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/schema";
import { errorMessage, settle } from "@/api/errors";
import i18n from "@/i18n";
import { AsyncState } from "@/stores/AsyncState";
import type { ToastStore } from "@/stores/ToastStore";

export type AdminUserRow = components["schemas"]["AdminUserRow"];
export type AdminUserCard = components["schemas"]["AdminUserCard"];
export type AdminLogEntry = components["schemas"]["AdminActionRead"];
export type ReplyReport = components["schemas"]["ReplyReportRead"];
export type UserFilter = "all" | "unconfirmed" | "paid" | "active";
/** Whether the console opens: checked once per visit, before any admin page loads. */
export type AdminAccess = "unknown" | "open" | "second_factor" | "denied";

export const ADMIN_PAGE_SIZE = 25;

const FILTER_QUERY: Record<UserFilter, { confirmed?: boolean; paid?: boolean; active?: boolean }> =
  {
    all: {},
    unconfirmed: { confirmed: false },
    paid: { paid: true },
    active: { active: true },
  };

/**
 * The admin console (F18.6): finding accounts, one account's card and the support actions
 * on it, and the admin log for super admins. Nothing here ever holds a receipt (BRD N2).
 */
export class AdminStore {
  readonly listState = new AsyncState();
  readonly cardState = new AsyncState();
  readonly actionState = new AsyncState();
  readonly logState = new AsyncState();
  access: AdminAccess = "unknown";
  users: AdminUserRow[] = [];
  total = 0;
  page = 1;
  query = "";
  filter: UserFilter = "all";
  card: AdminUserCard | null = null;
  log: AdminLogEntry[] = [];
  /** Assistant replies users reported, newest first (F22.4.2). */
  reports: ReplyReport[] = [];
  readonly reportsState = new AsyncState();
  private readonly api: ApiClient;
  private readonly toastStore: ToastStore;

  constructor(api: ApiClient, toastStore: ToastStore) {
    this.api = api;
    this.toastStore = toastStore;
    makeAutoObservable<this, "api" | "toastStore">(
      this,
      { api: false, toastStore: false },
      { autoBind: true },
    );
  }

  /** Forget everything when the signed-in account changes. */
  reset(): void {
    this.access = "unknown";
    this.users = [];
    this.total = 0;
    this.page = 1;
    this.query = "";
    this.filter = "all";
    this.card = null;
    this.log = [];
  }

  get pages(): number {
    return Math.max(1, Math.ceil(this.total / ADMIN_PAGE_SIZE));
  }

  /**
   * Ask the server whether this session opens the console. An admin whose session was
   * opened with the password alone is told to use two-factor sign-in (F18.6.1).
   */
  async checkAccess(): Promise<void> {
    const response = await settle(() =>
      this.api.GET("/api/v1/admin/users", { params: { query: { limit: 1 } } }),
    );
    runInAction(() => {
      const code = (response.error as { code?: string } | undefined)?.code;
      if (response.error === undefined) this.access = "open";
      else if (code === "second_factor_required") this.access = "second_factor";
      else this.access = "denied";
    });
  }

  async loadUsers(): Promise<void> {
    this.listState.start();
    const response = await settle(() =>
      this.api.GET("/api/v1/admin/users", {
        params: {
          query: {
            q: this.query.trim(),
            limit: ADMIN_PAGE_SIZE,
            offset: (this.page - 1) * ADMIN_PAGE_SIZE,
            ...FILTER_QUERY[this.filter],
          },
        },
      }),
    );
    runInAction(() => {
      if (response.error !== undefined) {
        this.listState.fail(errorMessage(response.error, i18n.t("messages:admin.failed")));
        return;
      }
      this.users = response.data.items;
      this.total = response.data.total;
      this.listState.succeed();
    });
  }

  search(query: string): void {
    this.query = query;
    this.page = 1;
    void this.loadUsers();
  }

  chooseFilter(filter: UserFilter): void {
    this.filter = filter;
    this.page = 1;
    void this.loadUsers();
  }

  goToPage(page: number): void {
    this.page = page;
    void this.loadUsers();
  }

  async loadCard(userId: string): Promise<void> {
    if (this.card?.id !== userId) this.card = null;
    this.cardState.start();
    const response = await settle(() =>
      this.api.GET("/api/v1/admin/users/{user_id}", {
        params: { path: { user_id: userId } },
      }),
    );
    runInAction(() => {
      if (response.error !== undefined) {
        this.cardState.fail(errorMessage(response.error, i18n.t("messages:admin.failed")));
        return;
      }
      this.card = response.data;
      this.cardState.succeed();
    });
  }

  confirmEmail(userId: string): Promise<boolean> {
    return this.act(userId, "admin.emailConfirmed", () =>
      this.api.POST("/api/v1/admin/users/{user_id}/confirm-email", {
        params: { path: { user_id: userId } },
      }),
    );
  }

  sendConfirmation(userId: string): Promise<boolean> {
    return this.act(userId, "admin.linkSent", () =>
      this.api.POST("/api/v1/admin/users/{user_id}/send-confirmation", {
        params: { path: { user_id: userId } },
      }),
    );
  }

  sendPasswordReset(userId: string): Promise<boolean> {
    return this.act(userId, "admin.linkSent", () =>
      this.api.POST("/api/v1/admin/users/{user_id}/send-password-reset", {
        params: { path: { user_id: userId } },
      }),
    );
  }

  /** Show the account the first-sign-in setup again on its next visit (F23.9). */
  restartOnboarding(userId: string): Promise<boolean> {
    return this.act(userId, "admin.onboardingRestarted", () =>
      this.api.POST("/api/v1/admin/users/{user_id}/restart-onboarding", {
        params: { path: { user_id: userId } },
      }),
    );
  }

  /** Give the paid plan for `days` more days, with the reason kept in the log. */
  grantPlan(userId: string, days: number, reason: string): Promise<boolean> {
    return this.act(userId, "admin.planGranted", () =>
      this.api.POST("/api/v1/admin/users/{user_id}/grants", {
        params: { path: { user_id: userId } },
        body: { days, reason: reason.trim() },
      }),
    );
  }

  revokeGrant(userId: string, grantId: string): Promise<boolean> {
    return this.act(userId, "admin.planRevoked", () =>
      this.api.POST("/api/v1/admin/users/{user_id}/grants/{grant_id}/revoke", {
        params: { path: { user_id: userId, grant_id: grantId } },
      }),
    );
  }

  /** Appoint or remove an admin; the server allows it to super admins only. */
  setAdmin(userId: string, admin: boolean): Promise<boolean> {
    return this.act(userId, admin ? "admin.appointed" : "admin.removed", () =>
      this.api.PUT("/api/v1/admin/users/{user_id}/role", {
        params: { path: { user_id: userId } },
        body: { admin },
      }),
    );
  }

  async loadLog(): Promise<void> {
    this.logState.start();
    const response = await settle(() =>
      this.api.GET("/api/v1/admin/log", { params: { query: { limit: 100 } } }),
    );
    runInAction(() => {
      if (response.error !== undefined) {
        this.logState.fail(errorMessage(response.error, i18n.t("messages:admin.failed")));
        return;
      }
      this.log = response.data.items;
      this.logState.succeed();
    });
  }

  /** The assistant replies users reported, for an admin to read (F22.4.2). */
  async loadReports(): Promise<void> {
    this.reportsState.start();
    const response = await settle(() => this.api.GET("/api/v1/admin/reports", {}));
    runInAction(() => {
      if (response.error !== undefined) {
        this.reportsState.fail(errorMessage(response.error, i18n.t("messages:admin.failed")));
        return;
      }
      this.reports = response.data;
      this.reportsState.succeed();
    });
  }

  private async act(
    userId: string,
    done:
      | "admin.emailConfirmed"
      | "admin.linkSent"
      | "admin.planGranted"
      | "admin.planRevoked"
      | "admin.appointed"
      | "admin.removed"
      | "admin.onboardingRestarted",
    send: () => Promise<{ error?: unknown }>,
  ): Promise<boolean> {
    this.actionState.start();
    const response = await settle(send);
    const ok = response.error === undefined;
    runInAction(() => {
      if (!ok) {
        this.actionState.fail(errorMessage(response.error, i18n.t("messages:admin.failed")));
        return;
      }
      this.actionState.succeed();
      this.toastStore.showSuccess(i18n.t(`messages:${done}`));
    });
    if (ok) await this.loadCard(userId);
    return ok;
  }
}
