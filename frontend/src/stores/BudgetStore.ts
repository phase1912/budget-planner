import { makeAutoObservable, runInAction } from "mobx";

import type { components } from "@/api/schema";
import { apiClient } from "@/api/client";
import { errorMessage } from "@/api/errors";
import type { YearMonth } from "@/shared/purchaseDate";
import type { CategorySpend } from "./CategoriesStore";
import type { Receipt } from "./ReceiptStore";

export type MonthSummary = components["schemas"]["MonthSummaryResponse"];

function monthIndex({ year, month }: YearMonth): number {
  return year * 12 + (month - 1);
}

function fromIndex(index: number): YearMonth {
  return { year: Math.floor(index / 12), month: (index % 12) + 1 };
}

const pad = (n: number) => String(n).padStart(2, "0");

/** The month as a date filter: its first and last day, both included (BRD E2). */
export function monthRange({ year, month }: YearMonth): { start: string; end: string } {
  const lastDay = new Date(Date.UTC(year, month, 0)).getUTCDate();
  const prefix = `${String(year)}-${pad(month)}`;
  return {
    start: `${prefix}-01`,
    end: `${prefix}-${pad(lastDay)}`,
  };
}

/**
 * The month view's state: which month is shown, what it adds up to, where it
 * went by category and its receipts (BRD D1, D2 — F6.1).
 *
 * "The current month" comes from the browser's own clock, not the server's UTC
 * one: at 00:30 on 1 October in Warsaw it is already October for the user
 * (ADR-0009). The clock is injectable so tests can stand on any date.
 *
 * A change to any receipt calls `refresh()`, so a recalculated month shows
 * its new figure in the same session, without a reload (D6 — F6.5).
 */
export class BudgetStore {
  year: number;
  month: number;
  summary: MonthSummary | null = null;
  /** The month's receipts column: the newest of a running month, the biggest of a finished one. */
  receipts: Receipt[] = [];
  /** The month's spend per category, highest first, counted like its total (D1). */
  spend: CategorySpend[] = [];
  /** How many receipts the month holds in all, whatever their status. */
  receiptsInMonth = 0;
  isLoading = false;
  error: string | null = null;

  private opened = false;
  private request = 0;
  private readonly now: () => Date;

  constructor(now: () => Date = () => new Date()) {
    this.now = now;
    const current = this.current;
    this.year = current.year;
    this.month = current.month;
    makeAutoObservable<this, "now" | "request" | "opened">(
      this,
      { now: false, request: false, opened: false },
      {
        autoBind: true,
      },
    );
  }

  /** The user's current month, by their local calendar. */
  get current(): YearMonth {
    const today = this.now();
    return { year: today.getFullYear(), month: today.getMonth() + 1 };
  }

  /**
   * The user's date as YYYY-MM-DD, sent with every request: whether a month is
   * still running is decided by their clock, not the server's (ADR-0009, D4).
   */
  get today(): string {
    const now = this.now();
    return `${String(now.getFullYear())}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
  }

  /** The future has no receipts yet; the switcher stops at the current month. */
  get canGoForward(): boolean {
    return monthIndex(this) < monthIndex(this.current);
  }

  /** Show the user's current month. */
  showCurrentMonth(): Promise<void> {
    return this.showMonth(this.current);
  }

  /**
   * What the landing view calls when it appears: the current month the first
   * time, afterwards the month the user left it on, fetched afresh. Coming back
   * from correcting an August receipt lands on August, showing its new figure.
   */
  open(): Promise<void> {
    if (!this.opened) {
      this.opened = true;
      return this.showCurrentMonth();
    }
    return this.showMonth({ year: this.year, month: this.month });
  }

  /**
   * A receipt was added, corrected or deleted: fetch the shown month again,
   * since the server has just recalculated it (D6). Nothing to do before the
   * month view has been opened; it fetches when it is.
   */
  refresh(): Promise<void> {
    if (!this.opened) return Promise.resolve();
    return this.showMonth({ year: this.year, month: this.month });
  }

  /** Forget everything: a different user is signing in. */
  reset(): void {
    this.request++;
    const current = this.current;
    this.year = current.year;
    this.month = current.month;
    this.summary = null;
    this.receipts = [];
    this.spend = [];
    this.receiptsInMonth = 0;
    this.isLoading = false;
    this.error = null;
    this.opened = false;
  }

  showPreviousMonth(): Promise<void> {
    return this.showMonth(fromIndex(monthIndex(this) - 1));
  }

  showNextMonth(): Promise<void> {
    if (!this.canGoForward) return Promise.resolve();
    return this.showMonth(fromIndex(monthIndex(this) + 1));
  }

  /**
   * Load one month's figure, its spend by category and its receipts, in one
   * request (F6.7). A response that arrives after a newer request was made is
   * dropped, so clicking through months quickly never shows a stale total.
   */
  async showMonth({ year, month }: YearMonth): Promise<void> {
    const request = ++this.request;
    this.year = year;
    this.month = month;
    this.isLoading = true;
    this.error = null;
    try {
      const response = await apiClient.GET("/api/v1/budget/months/{year}/{month}/dashboard", {
        params: { path: { year, month }, query: { today: this.today } },
      });
      if (response.error) {
        throw new Error(errorMessage(response.error, "Could not load the month"));
      }
      if (request !== this.request) return;
      const { summary, receipts, categories, receipts_in_month } = response.data;
      runInAction(() => {
        this.summary = summary;
        this.receipts = receipts;
        this.spend = categories;
        this.receiptsInMonth = receipts_in_month;
        this.isLoading = false;
      });
    } catch (error) {
      if (request !== this.request) return;
      runInAction(() => {
        this.error = error instanceof Error ? error.message : "Could not load the month";
        this.isLoading = false;
      });
    }
  }
}
