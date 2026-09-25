import { fireEvent, render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { MonthSummary } from "@/stores/BudgetStore";
import { DashboardPage } from "./DashboardPage";

const budgetStore = {
  year: 2026,
  month: 9,
  current: { year: 2026, month: 9 },
  summary: null as MonthSummary | null,
  isLoading: false,
  error: null as string | null,
  canGoForward: false,
  showCurrentMonth: vi.fn(),
  showPreviousMonth: vi.fn(),
  showNextMonth: vi.fn(),
};

vi.mock("@/stores/StoreContext", () => ({
  useStores: () => ({
    budgetStore,
    authStore: {
      user: { email: "test@example.com", first_name: "Anna", last_name: "Smith", currency: "PLN" },
    },
  }),
}));

function renderPage() {
  render(
    <BrowserRouter>
      <DashboardPage />
    </BrowserRouter>,
  );
}

function summary(overrides: Partial<MonthSummary> = {}): MonthSummary {
  return {
    year: 2026,
    month: 9,
    total: "1234.5",
    receipt_count: 15,
    has_receipts: true,
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
    });
  });

  it("opens on the current month", () => {
    renderPage();
    expect(budgetStore.showCurrentMonth).toHaveBeenCalled();
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
    expect(screen.getByText("15 receipts")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next month" })).toBeDisabled();
  });

  it("a past month reads as spent, not spent so far, and can step forward", () => {
    Object.assign(budgetStore, { year: 2026, month: 8, canGoForward: true });
    budgetStore.summary = summary({ month: 8, total: "80", receipt_count: 1 });
    renderPage();

    expect(screen.getByText("Spent in August")).toBeInTheDocument();
    expect(screen.getByText("1 receipt")).toBeInTheDocument();
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
});
