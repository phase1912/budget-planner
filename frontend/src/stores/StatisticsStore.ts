import { makeAutoObservable, runInAction } from "mobx";

import type { components } from "@/api/schema";
import { apiClient } from "@/api/client";
import { errorMessage } from "@/api/errors";
import i18n from "@/i18n";
import { device } from "@/platform";

export type CategoryStatistics = components["schemas"]["CategoryStatisticsResponse"];
export type DailySpend = components["schemas"]["DailySpendResponse"];
type Receipt = components["schemas"]["ReceiptResponse"];

/** The quick periods above the table (docs/design/screens/statistics.html). */
export type Preset =
  "this_month" | "last_month" | "last_3_months" | "last_6_months" | "this_year" | "custom";

/** How the day-by-day chart is drawn (F23.22.2). */
export type ChartView = "columns" | "days" | "calendar";
const CHART_VIEWS: ChartView[] = ["columns", "days", "calendar"];
const CHART_VIEW_KEY = "budget_chart_view";

/** The view this browser last chose; private windows and blocked storage get columns. */
function storedChartView(): ChartView {
  try {
    return CHART_VIEWS.find((v) => v === localStorage.getItem(CHART_VIEW_KEY)) ?? "columns";
  } catch {
    return "columns";
  }
}

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
  /** The period's receipts, newest first, once the Spending section asks (F23.4). */
  receipts: Receipt[] = [];
  receiptCount = 0;
  isLoadingReceipts = false;
  private receiptsWanted = false;
  chartView: ChartView = storedChartView();
  /** The day tapped on the chart and its receipts (F23.22.1); null until a tap. */
  day: string | null = null;
  dayReceipts: Receipt[] = [];
  isLoadingDay = false;
  isLoading = false;
  error: string | null = null;

  private request = 0;
  private readonly now: () => Date;

  constructor(now: () => Date = () => new Date()) {
    this.now = now;
    [this.start, this.end] = presetDays("this_month", now());
    makeAutoObservable<this, "request" | "now" | "receiptsWanted">(
      this,
      { request: false, now: false, receiptsWanted: false },
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

  /**
   * Open on a run of days, compared or not, as a link asked for it — the assistant's
   * answer card (F21.4) — and fetch it once.
   */
  show(start: string, end: string, compare: boolean): Promise<void> {
    this.compare = compare;
    return this.chooseRange(start, end);
  }

  /** Draw the chart another way, and keep the choice in this browser. */
  setChartView(view: ChartView): void {
    this.chartView = view;
    try {
      localStorage.setItem(CHART_VIEW_KEY, view);
    } catch {
      // Storage refused: the choice lasts until the page is closed.
    }
  }

  /** The receipts of one day tapped on the chart; a later tap's answer wins. */
  async openDay(day: string): Promise<void> {
    if (this.day !== day) void device.feel("selected");
    this.day = day;
    this.isLoadingDay = true;
    try {
      const response = await apiClient.GET("/receipts", {
        params: { query: { page: 1, size: 50, start: day, end: day } },
      });
      runInAction(() => {
        if (this.day !== day) return;
        this.dayReceipts = response.data?.items ?? [];
        this.isLoadingDay = false;
      });
    } catch {
      runInAction(() => {
        if (this.day === day) this.isLoadingDay = false;
      });
    }
  }

  /** Forget the figures: a different user is signing in. */
  reset(): void {
    this.request++;
    this.day = null;
    this.dayReceipts = [];
    this.statistics = null;
    this.daily = null;
    this.receipts = [];
    this.receiptCount = 0;
    this.isLoading = false;
    this.error = null;
  }

  /** Fetch the breakdown for the current period; a stale answer is dropped. */
  async load(): Promise<void> {
    const request = ++this.request;
    this.isLoading = true;
    this.error = null;
    // A day from the last period is not one of this one's.
    this.day = null;
    this.dayReceipts = [];
    void this.loadDaily(request);
    // A list already open follows the period.
    if (this.receiptsWanted) void this.loadReceipts();
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

  /**
   * The period's receipts, for Spending's own list — not the Receipts page's, whose
   * filters stay as the user left them there.
   */
  async loadReceipts(size = 20): Promise<void> {
    this.receiptsWanted = true;
    this.isLoadingReceipts = true;
    const [start, end] = [this.start, this.end];
    try {
      const response = await apiClient.GET("/receipts", {
        params: { query: { page: 1, size, start, end } },
      });
      runInAction(() => {
        if (start === this.start && end === this.end && response.data) {
          this.receipts = response.data.items;
          this.receiptCount = response.data.total;
        }
        this.isLoadingReceipts = false;
      });
    } catch {
      runInAction(() => {
        this.isLoadingReceipts = false;
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
    case "last_6_months":
      return [isoDay(new Date(year, month - 5, 1)), isoDay(today)];
    case "this_year":
      return [isoDay(new Date(year, 0, 1)), isoDay(today)];
  }
}
