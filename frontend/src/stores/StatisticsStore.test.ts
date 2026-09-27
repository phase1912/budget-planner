import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/api/client";
import { StatisticsStore } from "./StatisticsStore";

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
});
