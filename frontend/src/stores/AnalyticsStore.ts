import { makeAutoObservable, runInAction } from "mobx";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/schema";
import { errorMessage, settle } from "@/api/errors";
import i18n from "@/i18n";
import { device, type DeviceKind } from "@/platform";
import { AsyncState } from "@/stores/AsyncState";
import { isoDay, presetDays } from "@/stores/StatisticsStore";

export type UsageReport = components["schemas"]["UsageReportRead"];
export type ReportPeriod = "last_7" | "last_30" | "this_month";

/** The public pages whose views are counted; the API ignores any other path (F17.3.2). */
export const COUNTED_PAGES: ReadonlySet<string> = new Set([
  "/",
  "/en",
  "/uk",
  "/pl",
  "/help",
  "/privacy",
  "/terms",
  "/login",
  "/register",
]);

const DAY_MS = 86_400_000;

/** The first and last day of a report period, both included, ending today. */
export function reportDays(period: ReportPeriod, today: Date): [string, string] {
  if (period === "this_month") return presetDays("this_month", today);
  const back = period === "last_7" ? 6 : 29;
  return [isoDay(new Date(today.getTime() - back * DAY_MS)), isoDay(today)];
}

/**
 * The service's own analytics (F17.3): counting a view of a public page — page and
 * source only, nothing about the visitor — and, for admins, the dashboard's figures.
 */
/** What a view was opened in, as the server names it (F17.3.4). */
const PLATFORMS: Record<DeviceKind, "web" | "ios-app" | "android-app"> = {
  web: "web",
  ios: "ios-app",
  android: "android-app",
};

export class AnalyticsStore {
  readonly reportState = new AsyncState();
  report: UsageReport | null = null;
  period: ReportPeriod = "last_7";
  private readonly api: ApiClient;
  private referrerUsed = false;
  private lastCounted: { key: string; at: number } | null = null;

  constructor(api: ApiClient) {
    this.api = api;
    makeAutoObservable<this, "api" | "referrerUsed" | "lastCounted">(
      this,
      { api: false, referrerUsed: false, lastCounted: false },
      { autoBind: true },
    );
  }

  /**
   * Count one view of `path` if it is a public page and the reader is not signed in — a
   * user's own use is in their activity, not among visitors. The first page of a page load
   * is the visit, sent as `entry` with the referring site and campaign the API keeps the
   * domain or name of; later pages are views of the same visit. A failure is ignored.
   */
  countView(
    path: string,
    referrer: string,
    search: string,
    signedIn: boolean,
    now = Date.now(),
  ): void {
    if (signedIn || !COUNTED_PAGES.has(path)) return;
    // One opening, one count: an effect run twice for the same address is not a second view.
    const key = `${path}${search}`;
    if (this.lastCounted?.key === key && now - this.lastCounted.at < 1000) return;
    this.lastCounted = { key, at: now };
    const entry = !this.referrerUsed;
    this.referrerUsed = true;
    const utm = entry ? new URLSearchParams(search).get("utm_source") : null;
    void settle(() =>
      this.api.POST("/api/v1/analytics/views", {
        body: {
          page: path,
          referrer: entry && referrer ? referrer : null,
          utm_source: utm,
          entry,
          // The website or a store app; the system's family the server reads itself (F17.3.4).
          platform: PLATFORMS[device.kind],
        },
      }),
    );
  }

  choosePeriod(period: ReportPeriod): void {
    this.period = period;
    void this.loadReport();
  }

  /** The admin dashboard's figures for the chosen period, ending today (F17.3.3). */
  async loadReport(today: Date = new Date()): Promise<void> {
    const [start, end] = reportDays(this.period, today);
    this.reportState.start();
    const response = await settle(() =>
      this.api.GET("/api/v1/analytics/report", { params: { query: { start, end } } }),
    );
    runInAction(() => {
      if (response.error !== undefined) {
        this.reportState.fail(errorMessage(response.error, i18n.t("messages:account.failed")));
        return;
      }
      this.report = response.data;
      this.reportState.succeed();
    });
  }
}
