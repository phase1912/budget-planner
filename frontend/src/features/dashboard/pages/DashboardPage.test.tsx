import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { MonthSummary } from "@/stores/BudgetStore";
import type { CategorySpend } from "@/stores/CategoriesStore";
import type { Receipt } from "@/stores/ReceiptStore";
import { DashboardPage } from "./DashboardPage";

const budgetStore = {
  year: 2026,
  month: 9,
  current: { year: 2026, month: 9 },
  summary: null as MonthSummary | null,
  isLoading: false,
  error: null as string | null,
  canGoForward: false,
  isPastMonth: false,
  receipts: [] as Receipt[],
  spend: [] as CategorySpend[],
  receiptsInMonth: 0,
  open: vi.fn(),
  showPreviousMonth: vi.fn(),
  showNextMonth: vi.fn(),
};

const receiptStore = {
  selectedReceiptId: null as string | null,
  fetchReceiptDetail: vi.fn(),
};

// The dialogs have their own tests; here it only matters which receipt they are asked to open.
vi.mock("@/features/receipts/components/ReceiptDetailModal", () => ({
  ReceiptDetailModal: () => <div role="dialog" aria-label="Receipt detail" />,
}));
vi.mock("@/features/receipts/components/EditReceiptDialog", () => ({
  EditReceiptDialog: () => null,
}));
vi.mock("@/features/receipts/components/DeleteReceiptDialog", () => ({
  DeleteReceiptDialog: () => null,
}));

vi.mock("@/stores/StoreContext", () => ({
  useStores: () => ({
    budgetStore,
    receiptStore,
    authStore: {
      user: { email: "test@example.com", first_name: "Anna", last_name: "Smith", currency: "PLN" },
    },
  }),
}));

function WhereAmI() {
  const location = useLocation();
  return <output aria-label="Location">{location.pathname + location.search}</output>;
}

function renderPage() {
  render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="*" element={<WhereAmI />} />
      </Routes>
    </MemoryRouter>,
  );
}

function summary(overrides: Partial<MonthSummary> = {}): MonthSummary {
  return {
    year: 2026,
    month: 9,
    total: "1234.5",
    receipt_count: 15,
    has_receipts: true,
    excluded_count: 0,
    excluded_amount: "0",
    is_complete: false,
    days_elapsed: 26,
    days_in_month: 30,
    ...overrides,
  };
}

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.assign(budgetStore, {
      year: 2026,
      month: 9,
      summary: null,
      error: null,
      isLoading: false,
      canGoForward: false,
      isPastMonth: false,
      receipts: [],
      spend: [],
      receiptsInMonth: 0,
    });
    receiptStore.selectedReceiptId = null;
  });

  it("opens the month view, which picks the month to show", () => {
    renderPage();
    expect(budgetStore.open).toHaveBeenCalled();
  });

  it("welcomes a user who has no receipts yet", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 0, 1, 19));
    try {
      budgetStore.summary = summary({ total: "0", receipt_count: 0, has_receipts: false });
      renderPage();
      expect(screen.getByRole("heading", { name: "Good evening, Anna" })).toBeInTheDocument();
      expect(screen.queryByRole("navigation", { name: "Month" })).not.toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
  });

  it("shows what the current month adds up to so far", () => {
    budgetStore.summary = summary();
    renderPage();

    expect(screen.getByRole("heading", { name: "September 2026" })).toBeInTheDocument();
    expect(screen.getByText("Spent so far in September")).toBeInTheDocument();
    expect(screen.getByText("1,234.50")).toBeInTheDocument();
    expect(screen.getByText("PLN")).toBeInTheDocument();
    expect(screen.getByText("26 of 30 days recorded · 15 receipts")).toBeInTheDocument();
    expect(screen.getByText("Month-to-date · still running")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next month" })).toBeDisabled();
  });

  it("a past month reads as spent, not spent so far, and can step forward", () => {
    Object.assign(budgetStore, { year: 2026, month: 8, canGoForward: true });
    budgetStore.summary = summary({
      month: 8,
      total: "80",
      receipt_count: 1,
      is_complete: true,
      days_elapsed: 31,
      days_in_month: 31,
    });
    renderPage();

    expect(screen.getByText("Spent in August")).toBeInTheDocument();
    expect(screen.getByText("31 of 31 days · 1 receipt")).toBeInTheDocument();
    expect(screen.getByText("Finalised · complete month")).toBeInTheDocument();
    expect(screen.queryByText(/still running/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Next month" }));
    expect(budgetStore.showNextMonth).toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Previous month" }));
    expect(budgetStore.showPreviousMonth).toHaveBeenCalled();
  });

  it("says so when the month cannot be loaded", () => {
    budgetStore.error = "Server unavailable";
    renderPage();
    expect(screen.getByText("Server unavailable")).toBeInTheDocument();
  });

  it("names the receipts held out of the total and leads to them", () => {
    budgetStore.summary = summary({ excluded_count: 2, excluded_amount: "96.4" });
    renderPage();

    expect(
      screen.getByText(/2 receipts worth 96\.40 PLN are not in this total/),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Resolve them" })).toHaveAttribute(
      "href",
      "/receipts?status=manual_review",
    );
  });

  it("speaks of a single held-out receipt in the singular", () => {
    budgetStore.summary = summary({ excluded_count: 1, excluded_amount: "201.88" });
    renderPage();

    expect(
      screen.getByText(/1 receipt worth 201\.88 PLN is not in this total/),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Resolve it" })).toBeInTheDocument();
  });

  it("says nothing about exclusions when every receipt is counted", () => {
    budgetStore.summary = summary();
    renderPage();
    expect(screen.queryByRole("link", { name: /Resolve/ })).not.toBeInTheDocument();
  });

  it("lists a finished month's biggest receipts and opens one in place", () => {
    Object.assign(budgetStore, { year: 2026, month: 8, isPastMonth: true });
    budgetStore.summary = summary({ month: 8, is_complete: true });
    budgetStore.receipts = [
      receipt({ id: "pepco", merchant_name: "PEPCO", total_amount: "24", line_items: 3 }),
      receipt({ id: "held", merchant_name: "Biedronka", status: "manual_review" }),
    ];
    budgetStore.receiptsInMonth = 7;
    renderPage();

    expect(screen.getByRole("heading", { name: "Biggest receipts" })).toBeInTheDocument();
    expect(screen.getByText("4 Aug · 3 items")).toBeInTheDocument();
    expect(screen.getByText("Needs your review")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "All 7" })).toHaveAttribute(
      "href",
      "/receipts?start=2026-08-01&end=2026-08-31",
    );

    fireEvent.click(screen.getByRole("button", { name: /PEPCO/ }));
    expect(receiptStore.fetchReceiptDetail).toHaveBeenCalledWith("pepco");
  });

  it("lists a running month's latest receipts", () => {
    budgetStore.summary = summary();
    renderPage();
    expect(screen.getByRole("heading", { name: "Latest receipts" })).toBeInTheDocument();
  });

  it("shows where the month went and opens a category's items for that month", () => {
    Object.assign(budgetStore, { year: 2026, month: 8 });
    budgetStore.summary = summary({ month: 8 });
    budgetStore.spend = [
      { category_id: "groceries-id", name: "Groceries", item_count: 4, total_amount: "180.50" },
    ];
    renderPage();

    expect(screen.getByRole("heading", { name: "Where it went" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Groceries/ }));

    expect(screen.getByRole("status", { name: "Location" })).toHaveTextContent(
      "/categories?view=all&category=groceries-id&start=2026-08-01&end=2026-08-31",
    );
  });

  it("shows the receipt dialog over the month once one is picked", () => {
    budgetStore.summary = summary();
    receiptStore.selectedReceiptId = "pepco";
    renderPage();
    expect(screen.getByRole("dialog", { name: "Receipt detail" })).toBeInTheDocument();
  });
});

describe("DashboardPage — the month against its limit (D7)", () => {
  beforeEach(() => {
    Object.assign(budgetStore, { error: null, isLoading: false, receipts: [], spend: [] });
  });

  it("reads as a share of the limit, with what is left", () => {
    budgetStore.summary = summary({
      total: "1800",
      budget_limit: "3000.00",
      limit_percent: 60,
      limit_remaining: "1200.00",
    });
    renderPage();

    expect(screen.getByText("60% of your 3,000.00 PLN limit")).toBeInTheDocument();
    expect(screen.getByText("1,200.00 PLN left")).toBeInTheDocument();
    expect(screen.queryByText(/the mark is where the limit sat/)).not.toBeInTheDocument();
  });

  it("reads past 100% in the error tone and says by how much, never clamping", () => {
    budgetStore.summary = summary({
      total: "3248",
      is_complete: true,
      budget_limit: "3000.00",
      limit_percent: 108,
      limit_remaining: "-248.00",
    });
    renderPage();

    const share = screen.getByText("108% of your 3,000.00 PLN limit");
    expect(share).toHaveClass("text-error");
    expect(screen.getByText("Over by 248.00 PLN")).toHaveClass("text-error");
    expect(screen.getByText(/the mark is where the limit sat/)).toBeInTheDocument();
  });

  it("says nothing of a limit the user has not set", () => {
    budgetStore.summary = summary();
    renderPage();
    expect(screen.queryByText(/limit/)).not.toBeInTheDocument();
  });
});

function receipt({
  line_items = 1,
  ...overrides
}: Partial<Omit<Receipt, "line_items">> & { line_items?: number }): Receipt {
  return {
    id: "r",
    merchant_name: "Shop",
    transaction_date: "2026-08-04T23:30:00Z",
    total_amount: "10",
    status: "parsed",
    file_ids: [],
    created_at: "2026-08-05T08:00:00Z",
    line_items: Array.from({ length: line_items }, (_, i) => ({ id: String(i) })),
    ...overrides,
  } as Receipt;
}
