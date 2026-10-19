import { makeAutoObservable, runInAction } from "mobx";

import type { components } from "@/api/schema";
import { apiClient } from "@/api/client";
import { errorMessage, settle } from "@/api/errors";
import { AsyncState } from "@/stores/AsyncState";
import type { ToastStore } from "@/stores/ToastStore";
import i18n from "@/i18n";

export type Household = components["schemas"]["HouseholdRead"];
export type HouseholdMember = components["schemas"]["HouseholdMemberRead"];
export type HouseholdInvite = components["schemas"]["HouseholdInvite"];
export type HouseholdMonth = components["schemas"]["HouseholdMonthResponse"];
export type HouseholdStatistics = components["schemas"]["HouseholdStatisticsResponse"];
export type HouseholdDaily = components["schemas"]["HouseholdDailyResponse"];
export type HouseholdView = "mine" | "household";

/** Today by the browser's own calendar, as YYYY-MM-DD: whether a month is over is the user's call (ADR-0009). */
function localToday(now: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${String(now.getFullYear())}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/**
 * The signed-in user's household (E12 — F12.2, ADR-0017): who is in it, and the owner's
 * and members' actions on it. `household` is null both before loading and for a user
 * with none; `loaded` tells the two apart.
 */
export class HouseholdStore {
  household: Household | null = null;
  loaded = false;
  /** Whether the dashboard and statistics show the user's own figures or the household's (F12.5). */
  view: HouseholdView = "mine";
  month: HouseholdMonth | null = null;
  readonly monthState = new AsyncState();
  statistics: HouseholdStatistics | null = null;
  readonly statisticsState = new AsyncState();
  /** Each member's spending day by day over the statistics' period. */
  daily: HouseholdDaily | null = null;
  // Only the latest request may land: switching month or period quickly must not let
  // an older answer arrive last and overwrite the one asked for.
  private monthRequest = 0;
  private statisticsRequest = 0;
  private dailyRequest = 0;
  readonly saveState = new AsyncState();
  private readonly toastStore: ToastStore;

  constructor(toastStore: ToastStore) {
    this.toastStore = toastStore;
    makeAutoObservable(this, {}, { autoBind: true });
  }

  /** Whether the user owns their household and may manage it. */
  get isOwner(): boolean {
    return this.household?.my_role === "owner";
  }

  /** Whether there is anyone to share with: a household of one has no household view. */
  get shared(): boolean {
    return (this.household?.members.length ?? 0) > 1;
  }

  /** Whether the household's figures are what the user is looking at. */
  get showingHousehold(): boolean {
    return this.shared && this.view === "household";
  }

  setView(view: HouseholdView): void {
    this.view = view;
  }

  /** The household's spend in one month, against its budget, split by member (F12.5). */
  async loadMonth(year: number, month: number, now: Date = new Date()): Promise<void> {
    this.monthState.start();
    const request = ++this.monthRequest;
    const response = await settle(() =>
      apiClient.GET("/api/v1/household/months/{year}/{month}", {
        params: { path: { year, month }, query: { today: localToday(now) } },
      }),
    );
    runInAction(() => {
      if (request !== this.monthRequest) return;
      if (response.error) {
        this.monthState.fail(
          errorMessage(response.error, i18n.t("messages:household.monthFailed")),
        );
        return;
      }
      this.month = response.data;
      this.monthState.succeed();
    });
  }

  /** The household's spend by category over `start`-`end`, private as one row (F12.5). */
  async loadStatistics(start: string, end: string): Promise<void> {
    this.statisticsState.start();
    const request = ++this.statisticsRequest;
    const response = await settle(() =>
      apiClient.GET("/api/v1/household/statistics", { params: { query: { start, end } } }),
    );
    runInAction(() => {
      if (request !== this.statisticsRequest) return;
      if (response.error) {
        this.statisticsState.fail(
          errorMessage(response.error, i18n.t("messages:household.statisticsFailed")),
        );
        return;
      }
      this.statistics = response.data;
      this.statisticsState.succeed();
    });
  }

  /**
   * Each member's spending day by day between two dates (F12.5, F23.4). A failure only
   * leaves the chart out: the categories still show.
   */
  async loadDaily(start: string, end: string): Promise<void> {
    const request = ++this.dailyRequest;
    const response = await settle(() =>
      apiClient.GET("/api/v1/household/daily", { params: { query: { start, end } } }),
    );
    runInAction(() => {
      if (request !== this.dailyRequest) return;
      this.daily = response.error ? null : response.data;
    });
  }

  /** Set or clear the household's monthly budget; the owner only (F12.5, D7). */
  async setBudget(limit: string | null): Promise<boolean> {
    return this.save(
      () => apiClient.PUT("/api/v1/household/budget", { body: { budget_limit: limit } }),
      i18n.t("messages:household.budgetFailed"),
      limit === null
        ? i18n.t("messages:household.budgetRemoved")
        : i18n.t("messages:household.budgetSaved"),
    );
  }

  /** Read the household, if the user has one. */
  async load(): Promise<void> {
    const response = await settle(() => apiClient.GET("/api/v1/household"));
    runInAction(() => {
      if (!response.error) this.household = response.data ?? null;
      this.loaded = true;
    });
  }

  /** Start a household the user owns. */
  async create(name: string): Promise<boolean> {
    return this.save(
      () => apiClient.POST("/api/v1/household", { body: { name } }),
      i18n.t("messages:household.createFailed"),
      i18n.t("messages:household.created"),
    );
  }

  /** Rename the household; the owner only. */
  async rename(name: string): Promise<boolean> {
    return this.save(
      () => apiClient.PATCH("/api/v1/household", { body: { name } }),
      i18n.t("messages:household.renameFailed"),
      i18n.t("messages:household.renamed"),
    );
  }

  /** The owner takes a member out; their access to shared receipts ends at once. */
  async removeMember(userId: string): Promise<boolean> {
    return this.save(
      () =>
        apiClient.DELETE("/api/v1/household/members/{user_id}", {
          params: { path: { user_id: userId } },
        }),
      i18n.t("messages:household.removeFailed"),
      i18n.t("messages:household.removed"),
    );
  }

  /** Leave the household; the last one out deletes it. */
  async leave(): Promise<boolean> {
    this.saveState.start();
    const response = await settle(() => apiClient.POST("/api/v1/household/leave"));
    return runInAction(() => {
      if (response.error)
        return this.failed(response.error, i18n.t("messages:household.leaveFailed"));
      this.household = null;
      this.saveState.succeed();
      this.toastStore.showSuccess(i18n.t("messages:household.left"));
      return true;
    });
  }

  /** Replace the invite link; the old one stops working at once. The owner only. */
  async regenerateInvite(): Promise<boolean> {
    return this.save(
      () => apiClient.POST("/api/v1/household/invite/regenerate"),
      i18n.t("messages:household.inviteFailed"),
      i18n.t("messages:household.inviteMade"),
    );
  }

  /** The invite link for this household, or null for anyone but its owner. */
  inviteLink(origin: string): string | null {
    const code = this.household?.invite_code;
    return code ? `${origin}/join/${code}` : null;
  }

  /**
   * Whose household an invite link leads to (F12.3), or the reason it leads nowhere.
   * Shown before joining so nobody joins a stranger's household by mistake.
   */
  async readInvite(code: string): Promise<{ invite?: HouseholdInvite; error?: string }> {
    const response = await settle(() =>
      apiClient.GET("/api/v1/household/invites/{code}", { params: { path: { code } } }),
    );
    if (response.error) {
      return { error: errorMessage(response.error, i18n.t("messages:household.inviteInvalid")) };
    }
    return { invite: response.data };
  }

  /**
   * Join the household an invite link leads to. A refusal is left in `saveState.error`
   * for the join page to show beside the button, not raised as a toast as well.
   */
  async join(code: string): Promise<boolean> {
    return this.save(
      () => apiClient.POST("/api/v1/household/join", { body: { code } }),
      i18n.t("messages:household.joinFailed"),
      i18n.t("messages:household.joined"),
      { toastErrors: false },
    );
  }

  /** Forget everything: a different user is signing in. */
  reset(): void {
    this.household = null;
    this.loaded = false;
    this.view = "mine";
    this.month = null;
    this.statistics = null;
    this.daily = null;
  }

  private async save(
    send: () => Promise<{ data?: Household; error?: unknown }>,
    failure: string,
    success: string,
    { toastErrors = true }: { toastErrors?: boolean } = {},
  ): Promise<boolean> {
    this.saveState.start();
    const response = await settle(send);
    return runInAction(() => {
      if (response.error || !response.data)
        return this.failed(response.error, failure, toastErrors);
      this.household = response.data;
      this.saveState.succeed();
      this.toastStore.showSuccess(success);
      return true;
    });
  }

  private failed(error: unknown, fallback: string, toast = true): false {
    const message = errorMessage(error, fallback);
    this.saveState.fail(message);
    if (toast) this.toastStore.showError(message);
    return false;
  }
}
