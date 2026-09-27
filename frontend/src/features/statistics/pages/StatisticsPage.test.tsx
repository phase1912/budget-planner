import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { CategoryStatistics } from "@/stores/StatisticsStore";
import { StatisticsPage } from "./StatisticsPage";

const statisticsStore = {
  start: "2026-07-01",
  end: "2026-07-27",
  statistics: null as CategoryStatistics | null,
  isLoading: false,
  error: null as string | null,
  load: vi.fn(),
};

vi.mock("@/stores/StoreContext", () => ({
  useStores: () => ({ statisticsStore, authStore: { user: { currency: "PLN" } } }),
}));

function renderPage() {
  render(
    <MemoryRouter>
      <StatisticsPage />
    </MemoryRouter>,
  );
}

function july(overrides: Partial<CategoryStatistics> = {}): CategoryStatistics {
  return {
    start: "2026-07-01",
    end: "2026-07-27",
    total: "1128.60",
    item_count: 82,
    categories: [
      {
        category_id: "groceries-id",
        name: "Groceries",
        total: "742.60",
        share: "65.8",
        item_count: 68,
      },
      { category_id: "dining-id", name: "Dining", total: "386.00", share: "34.2", item_count: 14 },
    ],
    excluded_count: 0,
    excluded_amount: "0",
    ...overrides,
  };
}

describe("StatisticsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.assign(statisticsStore, { statistics: null, error: null, isLoading: false });
  });

  it("loads the period's statistics when opened", () => {
    renderPage();
    expect(statisticsStore.load).toHaveBeenCalled();
    expect(screen.getByText("1 – 27 Jul 2026")).toBeInTheDocument();
  });

  it("ranks every category with its total, share and item count", () => {
    statisticsStore.statistics = july();
    renderPage();

    const rows = within(screen.getByRole("table")).getAllByRole("row").slice(1);
    // The item count shows twice: in its column, and under the name for a phone.
    expect(rows.map((row) => row.textContent)).toEqual([
      "Groceries68 items742.6065.8%68",
      "Dining14 items386.0034.2%14",
    ]);
    expect(screen.getByRole("link", { name: "Groceries" })).toHaveAttribute(
      "href",
      "/categories?view=all&category=groceries-id&start=2026-07-01&end=2026-07-27",
    );
  });

  it("names the items left out because their receipts await review", () => {
    statisticsStore.statistics = july({ excluded_count: 2, excluded_amount: "96.4" });
    renderPage();
    expect(screen.getByText(/2 items worth 96\.40 PLN are left out/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Review them" })).toHaveAttribute(
      "href",
      "/receipts?status=manual_review",
    );
  });

  it("says plainly when nothing was spent in the period", () => {
    statisticsStore.statistics = july({ categories: [], total: "0", item_count: 0 });
    renderPage();
    expect(screen.getByText("Nothing was spent in 1 – 27 Jul 2026.")).toBeInTheDocument();
  });

  it("says why the statistics could not be loaded", () => {
    statisticsStore.error = "Server unavailable";
    renderPage();
    expect(screen.getByText("Server unavailable")).toBeInTheDocument();
  });
});
