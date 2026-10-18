import { makeAutoObservable, runInAction } from "mobx";

import type { components } from "@/api/schema";
import { apiClient } from "@/api/client";
import { errorMessage } from "@/api/errors";
import i18n from "@/i18n";

export type CategoryStatistics = components["schemas"]["CategoryStatisticsResponse"];
export type DailySpend = components["schemas"]["DailySpendResponse"];

/** The quick periods above the table (docs/design/screens/statistics.html). */
export type Preset = "this_month" | "last_month" | "last_3_months" | "custom";

const pad = (n: number) => String(n).padStart(2, "0");
/** A local day as YYYY-MM-DD, the form the API's periods take. */
export const isoDay = (d: Date) =>
  `${String(d.getFullYear())}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

/**
 * The statistics screen's state: which days it covers and the ranked category
 * breakdown for them (BRD E1, E2, E4 — F7.1, F7.2).
 *
 * A period is a run of whole days, both ends included, sent as YYYY-MM-DD —
 * the rule the API applies to every date filter. It opens on this month so far,
 * by the browser's own calendar (ADR-0009), as statistics.html does; a preset
 * or any custom range replaces it. The clock is injectable for tests.
 */
export class StatisticsStore {
  start: string;
  end: string;
  preset: Preset = "this_month";
  /** Whether each category is also measured against the previous period (E3). */
  compare = false;
  statistics: CategoryStatistics | null = null;
  /** Spending day by day over the same period (F23.4); null until loaded or if it failed. */
  daily: DailySpend | null = null;
  isLoading = false;
  error: string | null = null;

  private request = 0;
  private readonly now: () => Date;

  constructor(now: () => Date = () => new Date()) {
    this.now = now;
    [this.start, this.end] = presetDays("this_month", now());
    makeAutoObservable<this, "request" | "now">(
      this,
      { request: false, now: false },
      { autoBind: true },
    );
  }

  /** Turn the comparison with the previous like-for-like period on or off (BRD E3). */
  setCompare(on: boolean): Promise<void> {
    this.compare = on;
    return this.load();
  }

  /** Switch to a quick period and fetch it; "custom" keeps the days until a range is picked. */
  choosePreset(preset: Exclude<Preset, "custom">): Promise<void> {
    this.preset = preset;
    [this.start, this.end] = presetDays(preset, this.now());
    return this.load();
  }

  /**
   * Show any run of days, `start` to `end` inclusive (BRD E2). A backwards
   * range is swapped rather than refused: the picker's two fields were simply
   * filled the other way round.
   */
  chooseRange(start: string, end: string): Promise<void> {
    this.preset = "custom";
    [this.start, this.end] = start <= end ? [start, end] : [end, start];
    return this.load();
  }

  /** Forget the figures: a different user is signing in. */
  reset(): void {
    this.request++;
    this.statistics = null;
    this.daily = null;
    this.isLoading = false;
    this.error = null;
  }

  /** Fetch the breakdown for the current period; a stale answer is dropped. */
  async load(): Promise<void> {
    const request = ++this.request;
    this.isLoading = true;
    this.error = null;
    void this.loadDaily(request);
    try {
      const response = await apiClient.GET("/api/v1/statistics/categories", {
        params: { query: { start: this.start, end: this.end, compare: this.compare, chart: true } },
      });
      if (response.error) {
        throw new Error(errorMessage(response.error, i18n.t("messages:statistics.loadFailed")));
      }
      if (request !== this.request) return;
      runInAction(() => {
        this.statistics = response.data;
        this.isLoading = false;
      });
    } catch (error) {
      if (request !== this.request) return;
      runInAction(() => {
        this.error =
          error instanceof Error ? error.message : i18n.t("messages:statistics.loadFailed");
        this.isLoading = false;
      });
    }
  }

  /** The days of the period; without them Spending still shows its ring and table. */
  private async loadDaily(request: number): Promise<void> {
    try {
      const response = await apiClient.GET("/api/v1/statistics/daily", {
        params: { query: { start: this.start, end: this.end, today: isoDay(this.now()) } },
      });
      if (request !== this.request) return;
      runInAction(() => {
        this.daily = response.error ? null : response.data;
      });
    } catch {
      if (request !== this.request) return;
      runInAction(() => {
        this.daily = null;
      });
    }
  }
}

/**
 * A preset's first and last day on the user's calendar. "Last 3 months" is this
 * month so far and the two before it, so it always includes today, as "This
 * month" does; "Last month" is the whole previous calendar month.
 */
export function presetDays(preset: Exclude<Preset, "custom">, today: Date): [string, string] {
  const year = today.getFullYear();
  const month = today.getMonth();
  switch (preset) {
    case "this_month":
      return [isoDay(new Date(year, month, 1)), isoDay(today)];
    case "last_month":
      return [isoDay(new Date(year, month - 1, 1)), isoDay(new Date(year, month, 0))];
    case "last_3_months":
      return [isoDay(new Date(year, month - 2, 1)), isoDay(today)];
  }
}
