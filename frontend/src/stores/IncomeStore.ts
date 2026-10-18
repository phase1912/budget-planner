import { makeAutoObservable, runInAction } from "mobx";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/schema";
import { errorMessage, settle } from "@/api/errors";
import i18n from "@/i18n";
import { AsyncState } from "@/stores/AsyncState";
import type { ToastStore } from "@/stores/ToastStore";

export type MonthIncome = components["schemas"]["MonthIncomeRead"];
export type IncomeDraft = components["schemas"]["IncomeDraft"];
export type IncomeEntry = components["schemas"]["IncomeRead"];
type IncomeRequestSchema = components["schemas"]["IncomeRequest"];
/** An entry as sent; `channel` is "manual" unless it was confirmed from a document. */
export type IncomeRequest = Omit<IncomeRequestSchema, "channel"> &
  Partial<Pick<IncomeRequestSchema, "channel">>;
export type Balance = components["schemas"]["BalanceRead"];

const pad = (n: number) => String(n).padStart(2, "0");

/**
 * Whether Home should ask if the salary has arrived (F23.10): in the running month, once
 * its payday is reached (31 meaning the month's last day, whatever its length), while
 * nothing is entered yet and a usual income is known to offer.
 */
export function paydayDue(
  today: string,
  payday: number | null | undefined,
  month: MonthIncome | null,
): boolean {
  if (!payday || !month || month.entered || month.total == null) return false;
  const [year, monthNumber, day] = today.split("-").map(Number) as [number, number, number];
  const lastDay = new Date(year, monthNumber, 0).getDate();
  return day >= Math.min(payday, lastDay);
}

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
  /** What a document says came in, waiting for the user to confirm (F23.11). */
  draft: IncomeDraft | null = null;
  readingDocument = false;
  readError: string | null = null;
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
    return this.save(() =>
      this.api.POST("/api/v1/income", { body: { channel: "manual", ...body } }),
    );
  }

  /**
   * Record money that came in today — the salary confirmed on payday, or what Home asks
   * for when the balance runs out — then re-read the shown month and the balance, both of
   * which it moves. `today` is the user's own date, as the balance is reckoned on it.
   */
  async receive(
    body: Omit<IncomeRequest, "received_on">,
    today: string,
    shown: { year: number; month: number },
  ): Promise<boolean> {
    const ok = await this.add({ ...body, received_on: today });
    if (ok) await Promise.all([this.load(shown.year, shown.month), this.loadBalance(today)]);
    return ok;
  }

  /** Change an entry; how it came in stays as it was, whatever `channel` says. */
  update(id: string, body: IncomeRequest): Promise<boolean> {
    return this.save(() =>
      this.api.PUT("/api/v1/income/{income_id}", {
        params: { path: { income_id: id } },
        body: { channel: "manual", ...body },
      }),
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

  /**
   * Have a payslip or transfer confirmation read (F23.11). Nothing is saved: the draft
   * waits in `draft` for the user to confirm or correct; a refusal is in `readError`.
   */
  async readDocument(file: File): Promise<void> {
    this.readingDocument = true;
    this.readError = null;
    this.draft = null;
    const body = new FormData();
    body.append("file", file);
    const response = await settle(() =>
      // @ts-expect-error openapi-fetch types do not correctly handle FormData
      this.api.POST("/api/v1/income/read", { body }),
    );
    runInAction(() => {
      this.readingDocument = false;
      if (response.error === undefined) this.draft = response.data;
      else this.readError = errorMessage(response.error, i18n.t("messages:income.readFailed"));
    });
  }

  clearDraft(): void {
    this.draft = null;
    this.readError = null;
  }

  reset(): void {
    this.request++;
    this.draft = null;
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
