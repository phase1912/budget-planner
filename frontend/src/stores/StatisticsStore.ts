import { makeAutoObservable, runInAction } from "mobx";

import type { components } from "@/api/schema";
import { apiClient } from "@/api/client";
import { errorMessage } from "@/api/errors";

export type CategoryStatistics = components["schemas"]["CategoryStatisticsResponse"];

const pad = (n: number) => String(n).padStart(2, "0");
const isoDay = (d: Date) =>
  `${String(d.getFullYear())}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

/**
 * The statistics screen's state: which days it covers and the ranked category
 * breakdown for them (BRD E1, E4 — F7.1).
 *
 * The period opens on this month so far, by the browser's own calendar, as
 * docs/design/screens/statistics.html does ("1 – 27 Jul 2026"); choosing
 * another range arrives with F7.2. The clock is injectable for tests.
 */
export class StatisticsStore {
  start: string;
  end: string;
  statistics: CategoryStatistics | null = null;
  isLoading = false;
  error: string | null = null;

  private request = 0;

  constructor(now: () => Date = () => new Date()) {
    const today = now();
    this.start = isoDay(new Date(today.getFullYear(), today.getMonth(), 1));
    this.end = isoDay(today);
    makeAutoObservable<this, "request">(this, { request: false }, { autoBind: true });
  }

  /** Forget the figures: a different user is signing in. */
  reset(): void {
    this.request++;
    this.statistics = null;
    this.isLoading = false;
    this.error = null;
  }

  /** Fetch the breakdown for the current period; a stale answer is dropped. */
  async load(): Promise<void> {
    const request = ++this.request;
    this.isLoading = true;
    this.error = null;
    try {
      const response = await apiClient.GET("/api/v1/statistics/categories", {
        params: { query: { start: this.start, end: this.end } },
      });
      if (response.error) {
        throw new Error(errorMessage(response.error, "Could not load the statistics"));
      }
      if (request !== this.request) return;
      runInAction(() => {
        this.statistics = response.data;
        this.isLoading = false;
      });
    } catch (error) {
      if (request !== this.request) return;
      runInAction(() => {
        this.error = error instanceof Error ? error.message : "Could not load the statistics";
        this.isLoading = false;
      });
    }
  }
}
