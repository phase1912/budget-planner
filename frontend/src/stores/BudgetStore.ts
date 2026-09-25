import { makeAutoObservable, runInAction } from "mobx";

import type { components } from "@/api/schema";
import { apiClient } from "@/api/client";
import { errorMessage } from "@/api/errors";

export type MonthSummary = components["schemas"]["MonthSummaryResponse"];

interface YearMonth {
  year: number;
  month: number;
}

function monthIndex({ year, month }: YearMonth): number {
  return year * 12 + (month - 1);
}

function fromIndex(index: number): YearMonth {
  return { year: Math.floor(index / 12), month: (index % 12) + 1 };
}

/**
 * The month view's state: which month is shown and what it adds up to (BRD D1, D2 — F6.1).
 *
 * "The current month" comes from the browser's own clock, not the server's UTC
 * one: at 00:30 on 1 October in Warsaw it is already October for the user
 * (ADR-0009). The clock is injectable so tests can stand on any date.
 */
export class BudgetStore {
  year: number;
  month: number;
  summary: MonthSummary | null = null;
  isLoading = false;
  error: string | null = null;

  private request = 0;
  private readonly now: () => Date;

  constructor(now: () => Date = () => new Date()) {
    this.now = now;
    const current = this.current;
    this.year = current.year;
    this.month = current.month;
    makeAutoObservable<this, "now" | "request">(
      this,
      { now: false, request: false },
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

  /** The future has no receipts yet; the switcher stops at the current month. */
  get canGoForward(): boolean {
    return monthIndex(this) < monthIndex(this.current);
  }

  /** Show the user's current month; the landing view always opens on it. */
  showCurrentMonth(): Promise<void> {
    return this.showMonth(this.current);
  }

  showPreviousMonth(): Promise<void> {
    return this.showMonth(fromIndex(monthIndex(this) - 1));
  }

  showNextMonth(): Promise<void> {
    if (!this.canGoForward) return Promise.resolve();
    return this.showMonth(fromIndex(monthIndex(this) + 1));
  }

  /**
   * Load one month's figure. A response that arrives after a newer request was
   * made is dropped, so clicking through months quickly never shows a stale total.
   */
  async showMonth({ year, month }: YearMonth): Promise<void> {
    const request = ++this.request;
    this.year = year;
    this.month = month;
    this.isLoading = true;
    this.error = null;
    try {
      const response = await apiClient.GET("/api/v1/budget/months/{year}/{month}", {
        params: { path: { year, month } },
      });
      if (response.error) {
        throw new Error(errorMessage(response.error, "Could not load the month"));
      }
      if (request !== this.request) return;
      runInAction(() => {
        this.summary = response.data;
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
