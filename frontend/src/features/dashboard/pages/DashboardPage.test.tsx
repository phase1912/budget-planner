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
});
