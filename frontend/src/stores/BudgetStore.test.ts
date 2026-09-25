import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/api/client";
import { BudgetStore } from "./BudgetStore";

vi.mock("@/api/client", () => ({ apiClient: { GET: vi.fn() } }));

function month(year: number, monthNumber: number, total = "0") {
  return {
    data: { year, month: monthNumber, total, receipt_count: 0, has_receipts: true },
    response: new Response(),
  };
}

/** 00:30 on 1 October in the user's own timezone: already October for them. */
const JUST_PAST_MIDNIGHT = () => new Date(2026, 9, 1, 0, 30);

describe("BudgetStore", () => {
  beforeEach(() => {
    vi.mocked(apiClient.GET).mockReset();
  });

  it("opens on the user's own current month, by their local clock", async () => {
    vi.mocked(apiClient.GET).mockResolvedValue(month(2026, 10));
    const store = new BudgetStore(JUST_PAST_MIDNIGHT);

    await store.showCurrentMonth();

    expect(apiClient.GET).toHaveBeenCalledWith("/api/v1/budget/months/{year}/{month}", {
      params: { path: { year: 2026, month: 10 } },
    });
    expect([store.year, store.month]).toEqual([2026, 10]);
    expect(store.canGoForward).toBe(false);
  });

  it("steps back across a year boundary and forward again, but not into the future", async () => {
    vi.mocked(apiClient.GET).mockResolvedValue(month(2026, 1));
    const store = new BudgetStore(() => new Date(2026, 0, 15));

    await store.showPreviousMonth();
    expect([store.year, store.month]).toEqual([2025, 12]);
    expect(store.canGoForward).toBe(true);

    await store.showNextMonth();
    expect([store.year, store.month]).toEqual([2026, 1]);

    vi.mocked(apiClient.GET).mockClear();
    await store.showNextMonth();
    expect([store.year, store.month]).toEqual([2026, 1]);
    expect(apiClient.GET).not.toHaveBeenCalled();
  });

  it("never shows a stale month when the user clicks through quickly", async () => {
    let answerAugust: (value: unknown) => void = () => undefined;
    vi.mocked(apiClient.GET)
      .mockReturnValueOnce(
        new Promise((resolve) => {
          answerAugust = resolve;
        }) as never,
      )
      .mockResolvedValueOnce(month(2026, 7, "70.00"));
    const store = new BudgetStore(() => new Date(2026, 8, 10));

    const august = store.showMonth({ year: 2026, month: 8 });
    await store.showMonth({ year: 2026, month: 7 });
    answerAugust(month(2026, 8, "80.00"));
    await august;

    expect(store.summary?.total).toBe("70.00");
    expect([store.year, store.month]).toEqual([2026, 7]);
  });

  it("says why a month could not be loaded", async () => {
    vi.mocked(apiClient.GET).mockResolvedValue({
      error: { detail: "Server unavailable" },
      response: new Response(),
    } as never);
    const store = new BudgetStore(() => new Date(2026, 8, 10));

    await store.showCurrentMonth();

    expect(store.error).toBe("Server unavailable");
    expect(store.isLoading).toBe(false);
  });
});
