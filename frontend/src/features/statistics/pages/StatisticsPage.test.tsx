import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { CategoryStatistics } from "@/stores/StatisticsStore";
import { StatisticsPage } from "./StatisticsPage";

const statisticsStore = {
  start: "2026-07-01",
  end: "2026-07-27",
  preset: "this_month",
  compare: false,
  statistics: null as CategoryStatistics | null,
  isLoading: false,
  error: null as string | null,
  load: vi.fn(),
  choosePreset: vi.fn(),
  chooseRange: vi.fn(),
  setCompare: vi.fn(),
  receipts: [] as unknown[],
  receiptCount: 0,
  isLoadingReceipts: false,
  loadReceipts: vi.fn(),
};

const receiptStore = { selectedReceiptId: null, fetchReceiptDetail: vi.fn() };
const categoriesStore = {
  reviewCount: 0,
  reviewQueue: [] as unknown[],
  loadReviewCount: vi.fn(),
  fetchReviewQueue: vi.fn(),
};
const incomeStore = {
  bills: [] as { id: string; name: string; amount: string }[],
  loadBills: vi.fn(),
};

vi.mock("@/features/receipts/components/ReceiptDetailModal", () => ({
  ReceiptDetailModal: () => null,
}));
vi.mock("@/features/receipts/components/DeleteReceiptDialog", () => ({
  DeleteReceiptDialog: () => null,
}));
vi.mock("@/features/receipts/components/EditReceiptDialog", () => ({
  EditReceiptDialog: () => null,
}));

const exportStore = { busy: {} as Record<string, boolean>, start: vi.fn() };

vi.mock("@/stores/StoreContext", () => ({
  useStores: () => ({
    statisticsStore,
    exportStore,
    // Not in a household: the pages show only the user's own figures (F12.5).
    householdStore: { household: null, shared: false, showingHousehold: false, load: vi.fn() },
    authStore: { user: { currency: "PLN" } },
    receiptStore,
    categoriesStore,
    incomeStore,
  }),
}));

/** The chart and the table are folded until asked for. */
function openChartAndTable() {
  const toggle = screen.queryByRole("button", { name: /Chart and table/ });
  if (toggle) fireEvent.click(toggle);
}

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
    bills_total: "0.00",
    receipt_count: 20,
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
    Object.assign(statisticsStore, {
      statistics: null,
      error: null,
      isLoading: false,
      compare: false,
    });
  });

  it("loads the period's statistics when opened", () => {
    renderPage();
    expect(statisticsStore.load).toHaveBeenCalled();
    expect(screen.getAllByText("1 – 27 Jul 2026").length).toBeGreaterThan(0);
  });

  it("ranks every category with its total, share and item count", () => {
    statisticsStore.statistics = july();
    renderPage();
    openChartAndTable();

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

  it("says a period holds no receipts instead of showing a table of zeroes (E5)", () => {
    Object.assign(statisticsStore, { start: "2025-03-01", end: "2025-03-31" });
    statisticsStore.statistics = july({
      start: "2025-03-01",
      end: "2025-03-31",
      receipt_count: 0,
      total: null,
      item_count: null,
      categories: [],
    });
    renderPage();

    expect(screen.getByText("No receipts in March 2025")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Pick another period" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    Object.assign(statisticsStore, { start: "2026-07-01", end: "2026-07-27" });
  });

  it("says when the only receipts in a period are waiting for review", () => {
    statisticsStore.statistics = july({
      categories: [],
      total: "0",
      item_count: 0,
      excluded_count: 1,
      excluded_amount: "30",
    });
    renderPage();
    openChartAndTable();
    expect(
      screen.getByText("Nothing is counted in 1 – 27 Jul 2026 until those receipts are reviewed."),
    ).toBeInTheDocument();
  });

  it("says there is nothing to compare against when the previous period is empty", () => {
    statisticsStore.compare = true;
    statisticsStore.statistics = july({
      comparison: {
        start: "2026-06-01",
        end: "2026-06-27",
        receipt_count: 0,
        total: null,
        item_count: null,
        stops_mid_month: true,
      },
    });
    renderPage();
    expect(
      screen.getByText("No receipts in 1 – 27 Jun 2026, so every category is new against it."),
    ).toBeInTheDocument();
    expect(screen.queryByText(/still running/)).not.toBeInTheDocument();
  });

  it("says why the statistics could not be loaded", () => {
    statisticsStore.error = "Server unavailable";
    renderPage();
    expect(screen.getByText("Server unavailable")).toBeInTheDocument();
  });

  it("switches to a preset period", () => {
    statisticsStore.statistics = july();
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Last month" }));
    expect(statisticsStore.choosePreset).toHaveBeenCalledWith("last_month");
  });

  it("opens the range picker on Custom and shows the chosen days", () => {
    statisticsStore.statistics = july();
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Custom" }));

    const picker = screen.getByRole("dialog");
    expect(within(picker).getByLabelText("From")).toHaveValue("2026-07-01");
    expect(within(picker).getByLabelText("To")).toHaveValue("2026-07-27");
    fireEvent.change(within(picker).getByLabelText("From"), { target: { value: "2026-07-10" } });
    fireEvent.change(within(picker).getByLabelText("To"), { target: { value: "2026-07-24" } });
    fireEvent.click(within(picker).getByRole("button", { name: "Apply filter" }));

    expect(statisticsStore.chooseRange).toHaveBeenCalledWith("2026-07-10", "2026-07-24");
  });

  it("turns the comparison on from the period bar", () => {
    statisticsStore.statistics = july();
    renderPage();
    fireEvent.click(screen.getByRole("switch", { name: /Compare with the previous period/ }));
    expect(statisticsStore.setCompare).toHaveBeenCalledWith(true);
  });

  it("adds the previous period and each change, and says a running month is like for like", () => {
    statisticsStore.compare = true;
    statisticsStore.statistics = july({
      categories: [
        {
          category_id: "groceries-id",
          name: "Groceries",
          total: "742.60",
          share: "65.8",
          item_count: 68,
          previous_total: "812.40",
          change: "-69.80",
          change_percent: "-8.6",
        },
      ],
      comparison: {
        start: "2026-06-01",
        end: "2026-06-27",
        receipt_count: 18,
        total: "812.40",
        item_count: 70,
        stops_mid_month: true,
      },
    });
    renderPage();
    openChartAndTable();

    expect(screen.getByRole("switch", { name: /Compare with 1 – 27 Jun 2026/ })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(screen.getByText(/July is still running/)).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "1 – 27 Jun 2026" })).toBeInTheDocument();
    // In full in its own column; for a phone, just the percentage under the amount.
    expect(screen.getByText("−69.80 · −8.6%")).toBeInTheDocument();
    expect(screen.getAllByText("−8.6%").length).toBeGreaterThan(0);
  });

  it("offers this month, last month and the year", () => {
    statisticsStore.statistics = july();
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: /This year/ }));
    expect(statisticsStore.choosePreset).toHaveBeenCalledWith("this_year");
  });

  it("opens the period's receipts in place, loading them only then", () => {
    statisticsStore.statistics = july();
    statisticsStore.receipts = [
      {
        id: "r1",
        merchant_name: "Lidl",
        transaction_date: "2026-07-03T10:00:00Z",
        created_at: "2026-07-03T10:00:00Z",
        total_amount: "45.00",
        status: "parsed",
      },
    ];
    statisticsStore.receiptCount = 30;
    renderPage();

    expect(statisticsStore.loadReceipts).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: /^Receipts/ }));
    expect(statisticsStore.loadReceipts).toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: /Lidl/ }));
    expect(receiptStore.fetchReceiptDetail).toHaveBeenCalledWith("r1");
    expect(screen.getByRole("link", { name: /All 30 receipts/ })).toHaveAttribute(
      "href",
      "/receipts?start=2026-07-01&end=2026-07-27",
    );
    statisticsStore.receipts = [];
  });

  it("lists the month's bills and the items still to file, each folded", () => {
    // The section's sum is what the bills came to over the period on show (F23.21).
    statisticsStore.statistics = july({ bills_total: "3000.00" });
    incomeStore.bills = [{ id: "b1", name: "Rent", amount: "3000.00" }];
    categoriesStore.reviewCount = 4;
    renderPage();

    expect(screen.getByRole("button", { name: /Regular bills/ })).toHaveTextContent("3,000 PLN");
    expect(screen.getByRole("button", { name: /Items without a category/ })).toHaveTextContent("4");
    expect(screen.queryByText("Rent")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /Regular bills/ }));
    expect(screen.getByText("Rent")).toBeInTheDocument();
    incomeStore.bills = [];
    categoriesStore.reviewCount = 0;
  });
});
