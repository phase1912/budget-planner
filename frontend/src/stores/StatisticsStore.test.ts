import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/api/client";
import { StatisticsStore, presetDays } from "./StatisticsStore";

vi.mock("@/api/client", () => ({ apiClient: { GET: vi.fn() } }));

const JULY = {
  start: "2026-07-01",
  end: "2026-07-27",
  total: "100.00",
  item_count: 3,
  categories: [],
  excluded_count: 0,
  excluded_amount: "0",
};

describe("StatisticsStore", () => {
  beforeEach(() => {
    vi.mocked(apiClient.GET).mockReset();
  });

  it("covers this month so far, by the user's own calendar", async () => {
    vi.mocked(apiClient.GET).mockResolvedValue({ data: JULY, response: new Response() });
    const store = new StatisticsStore(() => new Date(2026, 6, 27, 23, 30));

    await store.load();

    expect(apiClient.GET).toHaveBeenCalledWith("/api/v1/statistics/categories", {
      params: { query: { start: "2026-07-01", end: "2026-07-27" } },
    });
    expect(store.statistics?.total).toBe("100.00");
  });

  it("says why the statistics could not be loaded", async () => {
    vi.mocked(apiClient.GET).mockResolvedValue({
      error: { detail: "Server unavailable" },
      response: new Response(),
    } as never);
    const store = new StatisticsStore();

    await store.load();

    expect([store.error, store.isLoading]).toEqual(["Server unavailable", false]);
  });

  it("forgets the figures when a different user signs in", async () => {
    vi.mocked(apiClient.GET).mockResolvedValue({ data: JULY, response: new Response() });
    const store = new StatisticsStore();
    await store.load();

    store.reset();

    expect(store.statistics).toBeNull();
  });

  it("fetches a picked run of days, both ends as given", async () => {
    vi.mocked(apiClient.GET).mockResolvedValue({ data: JULY, response: new Response() });
    const store = new StatisticsStore(() => new Date(2026, 6, 27));

    await store.chooseRange("2026-07-10", "2026-07-24");

    expect([store.preset, store.start, store.end]).toEqual(["custom", "2026-07-10", "2026-07-24"]);
    expect(apiClient.GET).toHaveBeenLastCalledWith("/api/v1/statistics/categories", {
      params: { query: { start: "2026-07-10", end: "2026-07-24" } },
    });
  });

  it("puts a range picked the wrong way round the right way round", async () => {
    vi.mocked(apiClient.GET).mockResolvedValue({ data: JULY, response: new Response() });
    const store = new StatisticsStore();

    await store.chooseRange("2026-07-24", "2026-07-10");

    expect([store.start, store.end]).toEqual(["2026-07-10", "2026-07-24"]);
  });

  it("goes back from a custom range to a preset", async () => {
    vi.mocked(apiClient.GET).mockResolvedValue({ data: JULY, response: new Response() });
    const store = new StatisticsStore(() => new Date(2026, 6, 27));
    await store.chooseRange("2026-07-10", "2026-07-24");

    await store.choosePreset("this_month");

    expect([store.preset, store.start, store.end]).toEqual([
      "this_month",
      "2026-07-01",
      "2026-07-27",
    ]);
  });
});

describe("presetDays", () => {
  const JAN_15 = new Date(2026, 0, 15);

  it("reads this month so far, last month whole, and three months up to today", () => {
    expect(presetDays("this_month", JAN_15)).toEqual(["2026-01-01", "2026-01-15"]);
    expect(presetDays("last_month", JAN_15)).toEqual(["2025-12-01", "2025-12-31"]);
    expect(presetDays("last_3_months", JAN_15)).toEqual(["2025-11-01", "2026-01-15"]);
  });

  it("ends last month on its own last day, a leap February included", () => {
    expect(presetDays("last_month", new Date(2028, 2, 3))).toEqual(["2028-02-01", "2028-02-29"]);
  });
});
