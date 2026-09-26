import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/api/client";
import { BudgetStore, LISTED_RECEIPTS, monthRange } from "./BudgetStore";

vi.mock("@/api/client", () => ({ apiClient: { GET: vi.fn() } }));

function month(year: number, monthNumber: number, total = "0") {
  return {
    data: { year, month: monthNumber, total, receipt_count: 0, has_receipts: true },
    response: new Response(),
  };
}

const NO_RECEIPTS = {
  data: { items: [], total: 0, page: 1, size: 6, pages: 0 },
  response: new Response(),
};

const GROCERIES = { category_id: "g", name: "Groceries", item_count: 3, total_amount: "42.00" };
const NO_ITEMS = {
  data: { items: [], total: 0, page: 1, size: 1, pages: 0, categories: [GROCERIES] },
  response: new Response(),
};

/** Answer the month figure with `answer` and the latest-receipts list with nothing. */
function figure(answer: (year: number, month: number) => unknown) {
  vi.mocked(apiClient.GET).mockImplementation(((url: string, init: unknown) => {
    if (url === "/receipts") return Promise.resolve(NO_RECEIPTS);
    if (url === "/receipts/line-items") return Promise.resolve(NO_ITEMS);
    const { year, month } = (init as { params: { path: { year: number; month: number } } }).params
      .path;
    return answer(year, month);
  }) as never);
}

function monthsAsked(): [number, number][] {
  const calls = vi.mocked(apiClient.GET).mock.calls as unknown as [string, unknown][];
  return calls
    .filter(([url]) => url.startsWith("/api/v1/budget"))
    .map(([, init]) => {
      const { year, month } = (init as { params: { path: { year: number; month: number } } }).params
        .path;
      return [year, month];
    });
}

/** 00:30 on 1 October in the user's own timezone: already October for them. */
const JUST_PAST_MIDNIGHT = () => new Date(2026, 9, 1, 0, 30);

describe("BudgetStore", () => {
  beforeEach(() => {
    vi.mocked(apiClient.GET).mockReset();
  });

  it("opens on the user's own current month, by their local clock", async () => {
    figure((y, m) => Promise.resolve(month(y, m)));
    const store = new BudgetStore(JUST_PAST_MIDNIGHT);

    await store.showCurrentMonth();

    expect(apiClient.GET).toHaveBeenCalledWith("/api/v1/budget/months/{year}/{month}", {
      params: { path: { year: 2026, month: 10 }, query: { today: "2026-10-01" } },
    });
    expect([store.year, store.month]).toEqual([2026, 10]);
    expect(store.canGoForward).toBe(false);
  });

  it("steps back across a year boundary and forward again, but not into the future", async () => {
    figure((y, m) => Promise.resolve(month(y, m)));
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
    figure((y, m) =>
      m === 8
        ? new Promise((resolve) => {
            answerAugust = resolve;
          })
        : Promise.resolve(month(y, m, "70.00")),
    );
    const store = new BudgetStore(() => new Date(2026, 8, 10));

    const august = store.showMonth({ year: 2026, month: 8 });
    await store.showMonth({ year: 2026, month: 7 });
    answerAugust(month(2026, 8, "80.00"));
    await august;

    expect(store.summary?.total).toBe("70.00");
    expect([store.year, store.month]).toEqual([2026, 7]);
  });

  it("says why a month could not be loaded", async () => {
    figure(() =>
      Promise.resolve({ error: { detail: "Server unavailable" }, response: new Response() }),
    );
    const store = new BudgetStore(() => new Date(2026, 8, 10));

    await store.showCurrentMonth();

    expect(store.error).toBe("Server unavailable");
    expect(store.isLoading).toBe(false);
  });

  it("lists a finished month's biggest receipts and where it went, within its own bounds", async () => {
    figure((y, m) => Promise.resolve(month(y, m)));
    const store = new BudgetStore(() => new Date(2026, 8, 10));

    await store.showMonth({ year: 2026, month: 2 });

    const february = { start_date: "2026-02-01T00:00:00Z", end_date: "2026-02-28T23:59:59Z" };
    expect(apiClient.GET).toHaveBeenCalledWith("/receipts", {
      params: { query: { page: 1, size: LISTED_RECEIPTS, order: "largest", ...february } },
    });
    expect(apiClient.GET).toHaveBeenCalledWith("/receipts/line-items", {
      params: { query: { view: "all", page: 1, size: 1, ...february } },
    });
    expect(store.spend).toEqual([GROCERIES]);
  });

  it("lists the running month's newest receipts", async () => {
    figure((y, m) => Promise.resolve(month(y, m)));
    const store = new BudgetStore(() => new Date(2026, 8, 10));

    await store.showCurrentMonth();

    expect(store.isPastMonth).toBe(false);
    expect(apiClient.GET).toHaveBeenCalledWith("/receipts", {
      params: {
        query: {
          page: 1,
          size: LISTED_RECEIPTS,
          order: "newest",
          start_date: "2026-09-01T00:00:00Z",
          end_date: "2026-09-30T23:59:59Z",
        },
      },
    });
  });

  it("opens on the current month first, then on the month it was left on", async () => {
    figure((y, m) => Promise.resolve(month(y, m)));
    const store = new BudgetStore(() => new Date(2026, 8, 10));

    await store.open();
    await store.showPreviousMonth();
    await store.open();

    expect(monthsAsked()).toEqual([
      [2026, 9],
      [2026, 8],
      [2026, 8],
    ]);
  });

  it("refetches the shown month when a receipt changes, once the view has been opened", async () => {
    let august = "284.81";
    figure((y, m) => Promise.resolve(month(y, m, m === 8 ? august : "0")));
    const store = new BudgetStore(() => new Date(2026, 8, 10));

    await store.refresh();
    expect(apiClient.GET).not.toHaveBeenCalled();

    await store.open();
    await store.showPreviousMonth();
    august = "384.81";
    await store.refresh();

    expect([store.year, store.month, store.summary?.total]).toEqual([2026, 8, "384.81"]);
  });

  it("forgets the month and its figure when a different user signs in", async () => {
    figure((y, m) => Promise.resolve(month(y, m)));
    const store = new BudgetStore(() => new Date(2026, 8, 10));
    await store.open();
    await store.showPreviousMonth();

    store.reset();

    expect([store.year, store.month, store.summary, store.receipts, store.spend]).toEqual([
      2026,
      9,
      null,
      [],
      [],
    ]);
    vi.mocked(apiClient.GET).mockClear();
    await store.open();
    expect(monthsAsked()).toEqual([[2026, 9]]);
  });
});

describe("monthRange", () => {
  it("ends on the month's own last day, leap years and December included", () => {
    expect(monthRange({ year: 2028, month: 2 }).end).toBe("2028-02-29T23:59:59Z");
    expect(monthRange({ year: 2026, month: 12 })).toEqual({
      start: "2026-12-01T00:00:00Z",
      end: "2026-12-31T23:59:59Z",
    });
  });
});
