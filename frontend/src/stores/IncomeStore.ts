import { makeAutoObservable, runInAction } from "mobx";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/schema";
import { errorMessage, settle } from "@/api/errors";
import i18n from "@/i18n";
import { AsyncState } from "@/stores/AsyncState";
import type { ToastStore } from "@/stores/ToastStore";

export type MonthIncome = components["schemas"]["MonthIncomeRead"];
export type IncomeEntry = components["schemas"]["IncomeRead"];
export type IncomeRequest = components["schemas"]["IncomeRequest"];
export type Balance = components["schemas"]["BalanceRead"];

const pad = (n: number) => String(n).padStart(2, "0");

/**
 * Money coming in (F23.10): one month's entries and total — the usual income standing in
 * while the month has none — adding, changing and removing entries, and the balance they
 * move (F23.14).
 */
export class IncomeStore {
  readonly state = new AsyncState();
  readonly saveState = new AsyncState();
  month: MonthIncome | null = null;
  /** What the user has now (F23.14); null until loaded, `balance` null until a start is set. */
  balance: Balance | null = null;
  private readonly api: ApiClient;
  private readonly toastStore: ToastStore;
  private request = 0;

  constructor(api: ApiClient, toastStore: ToastStore) {
    this.api = api;
    this.toastStore = toastStore;
    makeAutoObservable<this, "api" | "toastStore" | "request">(
      this,
      { api: false, toastStore: false, request: false },
      { autoBind: true },
    );
  }

  /** The month's income as a number, or null when neither entered nor usual is known. */
  get total(): number | null {
    return this.month?.total == null ? null : Number(this.month.total);
  }

  async load(year: number, month: number): Promise<void> {
    const request = ++this.request;
    this.state.start();
    const key = `${String(year)}-${pad(month)}`;
    const response = await settle(() =>
      this.api.GET("/api/v1/income", { params: { query: { month: key } } }),
    );
    if (request !== this.request) return;
    runInAction(() => {
      if (response.error !== undefined) {
        this.state.fail(errorMessage(response.error, i18n.t("messages:income.failed")));
        return;
      }
      this.month = response.data;
      this.state.succeed();
    });
  }

  /**
   * Set what came in this month to one amount — the quick edit on Home. A month with one
   * entry has it changed; a month with none gets one, dated today if the month is running,
   * else its first day. A month of several entries is edited entry by entry in Plan.
   */
  async setMonthTotal(
    year: number,
    month: number,
    amount: string,
    source: string,
  ): Promise<boolean> {
    const entries = this.month?.entries ?? [];
    if (entries.length > 1) return false;
    const today = new Date();
    const running = today.getFullYear() === year && today.getMonth() + 1 === month;
    const day = running ? today.getDate() : 1;
    const body: IncomeRequest = entries[0]
      ? { ...entries[0], amount }
      : {
          received_on: `${String(year)}-${pad(month)}-${pad(day)}`,
          amount,
          source,
          kind: "salary",
        };
    const ok = entries[0] ? await this.update(entries[0].id, body) : await this.add(body);
    if (ok) await this.load(year, month);
    return ok;
  }

  add(body: IncomeRequest): Promise<boolean> {
    return this.save(() => this.api.POST("/api/v1/income", { body }));
  }

  update(id: string, body: IncomeRequest): Promise<boolean> {
    return this.save(() =>
      this.api.PUT("/api/v1/income/{income_id}", { params: { path: { income_id: id } }, body }),
    );
  }

  async remove(id: string): Promise<boolean> {
    return this.save(() =>
      this.api.DELETE("/api/v1/income/{income_id}", { params: { path: { income_id: id } } }),
    );
  }

  /** The balance on the user's own today; a failure leaves it unknown, Home works without it. */
  async loadBalance(today: string): Promise<void> {
    const response = await settle(() =>
      this.api.GET("/api/v1/income/balance", { params: { query: { today } } }),
    );
    runInAction(() => {
      if (response.error === undefined) this.balance = response.data;
    });
  }

  reset(): void {
    this.request++;
    this.month = null;
    this.balance = null;
    this.state.reset();
  }

  private async save(send: () => Promise<{ error?: unknown }>): Promise<boolean> {
    this.saveState.start();
    const response = await settle(send);
    const ok = response.error === undefined;
    runInAction(() => {
      if (ok) {
        this.saveState.succeed();
        this.toastStore.showSuccess(i18n.t("messages:income.saved"));
      } else {
        const message = errorMessage(response.error, i18n.t("messages:income.failed"));
        this.saveState.fail(message);
        this.toastStore.showError(message);
      }
    });
    return ok;
  }
}
