import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { MonthSummary } from "@/stores/BudgetStore";
import type { CategorySpend } from "@/stores/CategoriesStore";
import type { Receipt } from "@/stores/ReceiptStore";
import type { Trip } from "@/stores/TripsStore";
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
  trips: [] as Trip[],
  open: vi.fn(),
  showPreviousMonth: vi.fn(),
  showNextMonth: vi.fn(),
  refresh: vi.fn(),
  today: "2026-09-26",
};

const bankAccountsStore = {
  // Most of Home is seen by someone with a card; a test without one says so.
  accounts: [
    { id: "card", name: "My card", kind: "personal", for_purchases: true, shared: false },
  ] as Record<string, unknown>[],
  loaded: true,
  any: true,
  load: vi.fn(),
  byId: () => undefined,
  saveState: { isLoading: false },
};

const incomeStore = {
  month: null as null | {
    total: string | null;
    entered: boolean;
    entries: { amount: string }[];
    taxes?: string;
    net?: string | null;
    regular?: unknown[];
    bills_total?: string;
  },
  balance: null as null | { balance: string | null; since: string | null; from_accounts?: boolean },
  receive: vi.fn().mockResolvedValue(true),
  pending: [] as {
    id: string;
    amount: string | null;
    received_on: string | null;
    source: string | null;
    kind: "salary" | "side" | "refund" | "other";
  }[],
  loadPending: vi.fn(),
  confirmPending: vi.fn().mockResolvedValue(true),
  dismissPending: vi.fn(),
  saveState: { isLoading: false },
  load: vi.fn(),
  loadBalance: vi.fn(),
  setMonthTotal: vi.fn().mockResolvedValue(true),
};
const categoriesStore = { reviewCount: 0, loadReviewCount: vi.fn() };
const profileStore = { saveQuietly: vi.fn().mockResolvedValue(true) };
const productsStore = { overview: null, loadOverview: vi.fn() };

const authStore = {
  user: {
    email: "test@example.com",
    first_name: "Anna",
    last_name: "Smith",
    currency: "PLN",
    payday: null as number | null,
  },
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
    // Not in a household: the pages show only the user's own figures (F12.5).
    bankAccountsStore,
    householdStore: {
      household: null,
      mayShare: false,
      shared: false,
      showingHousehold: false,
      load: vi.fn(),
    },
    incomeStore,
    categoriesStore,
    profileStore,
    productsStore,
    adviceStore: { warnings: [], loadProgress: vi.fn(), dismissWarning: vi.fn() },
    installStore: { dismissed: false, offersInstall: false, showsIosHint: false },
    authStore,
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
    bills_total: "0.00",
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
      trips: [],
    });
    receiptStore.selectedReceiptId = null;
    incomeStore.month = null;
    categoriesStore.reviewCount = 0;
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

  it("shows a personal trip inside the total and a business trip as owed back (F20.1)", () => {
    budgetStore.summary = summary();
    const trip = {
      country: "EG",
      city: null,
      start_date: "2026-09-03",
      end_date: "2026-09-10",
      purpose: null,
      receipt_count: 4,
      asking_count: 0,
    };
    budgetStore.trips = [
      { ...trip, id: "t1", kind: "personal", name: "Egypt", total: "800.00" },
      { ...trip, id: "t2", kind: "business", name: "Berlin", total: "312.40" },
    ];
    renderPage();

    expect(screen.getByText("of which trip «Egypt»: 800.00 PLN")).toBeInTheDocument();
    expect(
      screen.getByText("business trip «Berlin», to be reimbursed: 312.40 PLN"),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open trip: Egypt" })).toHaveAttribute(
      "href",
      "/trips/t1",
    );
  });

  it("shows what the current month adds up to so far, with nothing to measure it against", () => {
    budgetStore.summary = summary();
    renderPage();

    expect(screen.getByRole("heading", { name: "September" })).toBeInTheDocument();
    expect(screen.getByText("Spent so far")).toBeInTheDocument();
    expect(screen.getByText("1,235")).toBeInTheDocument();
    expect(screen.getByText("26 of 30 days · 15 receipts")).toBeInTheDocument();
    expect(screen.getByText("Still running")).toBeInTheDocument();
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

    expect(screen.getByText("Spent")).toBeInTheDocument();
    expect(screen.getByText("31 of 31 days · 1 receipt")).toBeInTheDocument();
    expect(screen.getByText("Finalised")).toBeInTheDocument();
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

  it("names the receipts held out of the total and leads to them (D3)", () => {
    budgetStore.summary = summary({ excluded_count: 2, excluded_amount: "96.4" });
    renderPage();
    expect(
      screen.getByRole("link", { name: /2 receipts worth 96\.40 PLN sit outside this total/ }),
    ).toHaveAttribute("href", "/receipts?status=manual_review");
  });

  it("speaks of a single held-out receipt in the singular", () => {
    budgetStore.summary = summary({ excluded_count: 1, excluded_amount: "201.88" });
    renderPage();
    expect(
      screen.getByText(/1 receipt worth 201\.88 PLN sits outside this total/),
    ).toBeInTheDocument();
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
    expect(screen.getByText("Needs your review")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "All 7" })).toHaveAttribute(
      "href",
      "/receipts?start=2026-08-01&end=2026-08-31",
    );
    fireEvent.click(screen.getByRole("button", { name: /PEPCO/ }));
    expect(receiptStore.fetchReceiptDetail).toHaveBeenCalledWith("pepco");
  });

  it("shows where the month went as tiles leading to each category's items", () => {
    Object.assign(budgetStore, { year: 2026, month: 8 });
    budgetStore.summary = summary({ month: 8 });
    budgetStore.spend = [
      { category_id: "groceries-id", name: "Groceries", item_count: 4, total_amount: "180.50" },
    ];
    renderPage();

    expect(screen.getByRole("heading", { name: "Where it went" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Groceries/ })).toHaveAttribute(
      "href",
      "/categories?view=all&category=groceries-id&start=2026-08-01&end=2026-08-31",
    );
    expect(screen.getByRole("link", { name: "All statistics" })).toHaveAttribute(
      "href",
      "/spending",
    );
  });

  it("leads to the lines waiting for a category (F23.3)", () => {
    budgetStore.summary = summary();
    categoriesStore.reviewCount = 3;
    renderPage();
    expect(screen.getByRole("link", { name: /3 lines need a category/ })).toHaveAttribute(
      "href",
      "/categories",
    );
  });

  it("shows the receipt dialog over the month once one is picked", () => {
    budgetStore.summary = summary();
    receiptStore.selectedReceiptId = "pepco";
    renderPage();
    expect(screen.getByRole("dialog", { name: "Receipt detail" })).toBeInTheDocument();
  });
});

describe("DashboardPage — what is left (D7, F23.3)", () => {
  beforeEach(() => {
    Object.assign(budgetStore, { error: null, isLoading: false, receipts: [], spend: [] });
    incomeStore.month = null;
    incomeStore.balance = null;
    incomeStore.pending = [];
    authStore.user.payday = null;
  });

  it("shows a payslip that came by email and confirms it as checked", async () => {
    budgetStore.summary = summary();
    incomeStore.pending = [
      { id: "p1", amount: "7607.55", received_on: "2026-10-10", source: "ACME", kind: "salary" },
    ];
    renderPage();

    expect(screen.getByText("Came in by email · ACME")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Check and add" }));
    expect(screen.getByLabelText("Amount")).toHaveValue("7607.55");
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await vi.waitFor(() => {
      expect(incomeStore.confirmPending).toHaveBeenCalledWith(
        "p1",
        expect.objectContaining({ amount: "7607.55", source: "ACME", channel: "document" }),
      );
    });
  });

  it("dismisses a pending income without adding it", () => {
    budgetStore.summary = summary();
    incomeStore.pending = [
      { id: "p1", amount: "10.00", received_on: null, source: null, kind: "other" },
    ];
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(incomeStore.dismissPending).toHaveBeenCalledWith("p1");
  });

  it("asks for income when the balance has run out, and records what came in today", async () => {
    budgetStore.summary = summary();
    incomeStore.balance = { balance: "-120.00", since: "2026-09-01" };
    renderPage();

    expect(screen.getByText("Looks like money came in that isn't here")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Add income" }));
    fireEvent.change(screen.getByLabelText("Received today"), { target: { value: "500" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await vi.waitFor(() => {
      expect(incomeStore.receive).toHaveBeenCalledWith(
        { amount: "500", source: "Added on Home", kind: "other", shared: false },
        "2026-09-26",
        { year: 2026, month: 9 },
      );
    });
  });

  it("offers to set the balance again when it has run out", () => {
    budgetStore.summary = summary();
    incomeStore.balance = { balance: "0.00", since: "2026-09-01" };
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Correct the balance" }));
    expect(screen.getByLabelText("What you have today")).toBeInTheDocument();
  });

  it("on payday with nothing entered, records the usual salary in one tap", async () => {
    budgetStore.summary = summary();
    authStore.user.payday = 10;
    incomeStore.month = { total: "6800.00", entered: false, entries: [], regular: [] };
    renderPage();

    expect(screen.getByText("Has your salary arrived?")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Yes, add it" }));

    await vi.waitFor(() => {
      expect(incomeStore.receive).toHaveBeenCalledWith(
        { amount: "6800.00", source: "Salary", kind: "salary", shared: false },
        "2026-09-26",
        { year: 2026, month: 9 },
      );
    });
  });

  it("does not ask about the salary once the month has income entered", () => {
    budgetStore.summary = summary();
    authStore.user.payday = 10;
    incomeStore.month = { total: "6800.00", entered: true, entries: [], regular: [] };
    renderPage();

    expect(screen.queryByText("Has your salary arrived?")).toBeNull();
  });

  it("reads what is left of the budget, and what was spent on a tap", () => {
    budgetStore.summary = summary({ total: "1800", budget_limit: "3000.00" });
    renderPage();

    expect(screen.getByText("left of your budget")).toBeInTheDocument();
    expect(screen.getByText("1,200")).toBeInTheDocument();
    expect(screen.getByText("3,000 PLN")).toBeInTheDocument();
    // 1 200 left over the 5 days that remain of a 30-day month on day 26.
    expect(screen.getByText("240 PLN a day")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Tap for the next view/ }));
    expect(screen.getByText("1,800")).toBeInTheDocument();
  });

  it("moves the ring from the budget to the income to the categories, a tap at a time", () => {
    budgetStore.summary = summary({ total: "1800", budget_limit: "3000.00" });
    budgetStore.spend = [
      { category_id: "g", name: "Groceries", item_count: 4, total_amount: "1800.00" },
    ];
    incomeStore.month = { total: "6800.00", entered: true, entries: [], regular: [] };
    renderPage();

    expect(screen.getByText("left of your budget")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Tap for the next view/ }));
    expect(screen.getByText("left of what came in")).toBeInTheDocument();
    expect(screen.getByText("5,000")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Tap for the next view/ }));
    expect(screen.getByRole("img", { name: /by category/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Tap for the next view/ }));
    expect(screen.getByText("left of your budget")).toBeInTheDocument();
  });

  it("measures what is left against income after tax for one who pays their own", () => {
    budgetStore.summary = summary({ total: "1800" });
    incomeStore.month = {
      total: "6800.00",
      entered: true,
      entries: [],
      taxes: "1800.00",
      net: "5000.00",
    };
    renderPage();

    expect(screen.getByText("Income · after tax")).toBeInTheDocument();
    expect(screen.getByText("5,000 PLN")).toBeInTheDocument();
    expect(screen.getByText("3,200")).toBeInTheDocument();
  });

  it("takes the month's bills off what came in before what was spent", () => {
    budgetStore.summary = summary({ total: "1800", bills_total: "3000.00" });
    incomeStore.month = {
      total: "6800.00",
      entered: true,
      entries: [],
      regular: [],
      bills_total: "3000.00",
    };
    renderPage();

    expect(screen.getByText("left of what came in")).toBeInTheDocument();
    expect(screen.getByText("2,000")).toBeInTheDocument();
  });

  it("says by how much a month went over, never clamping", () => {
    budgetStore.summary = summary({ total: "3248", is_complete: true, budget_limit: "3000.00" });
    renderPage();
    expect(screen.getByText("over budget")).toBeInTheDocument();
    expect(screen.getByText("248")).toBeInTheDocument();
  });

  it("measures against the income when there is no budget, marking the usual one", () => {
    budgetStore.summary = summary({ total: "1800" });
    incomeStore.month = { total: "6800.00", entered: false, entries: [], regular: [] };
    renderPage();
    expect(screen.getByText("left of what came in")).toBeInTheDocument();
    expect(screen.getByText("5,000")).toBeInTheDocument();
    expect(screen.getByText("Income · usual")).toBeInTheDocument();
  });

  it("changes the month's income in place", async () => {
    budgetStore.summary = summary();
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: /Income/ }));
    fireEvent.change(screen.getByLabelText("What came in"), { target: { value: "6 200,50" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await vi.waitFor(() => {
      expect(incomeStore.setMonthTotal).toHaveBeenCalledWith(2026, 9, "6200.50", "Salary");
    });
  });

  it("keeps no balance with a budget alone, and counts bills against the budget (F23.21)", () => {
    budgetStore.summary = summary({ total: "300", budget_limit: "2000.00", bills_total: "60.00" });
    renderPage();

    expect(screen.queryByRole("button", { name: /Add what you have now/ })).toBeNull();
    expect(screen.getByText("left of your budget")).toBeInTheDocument();
    expect(screen.getByText("1,640")).toBeInTheDocument();
  });

  it("corrects a balance kept from a start in place, as what is there now", async () => {
    budgetStore.summary = summary();
    incomeStore.balance = { balance: "4000.00", since: "2026-09-01" };
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: /On your accounts/ }));
    expect(screen.getByText(/Not your income/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("What you have today"), { target: { value: "5000" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await vi.waitFor(() => {
      expect(profileStore.saveQuietly).toHaveBeenCalledWith({
        starting_balance: "5000",
        balance_since: "2026-09-26",
      });
    });
    incomeStore.balance = null;
  });

  it("with no card yet, adds income where the card it lands on is made (F23.21)", () => {
    budgetStore.summary = summary();
    const cards = bankAccountsStore.accounts;
    bankAccountsStore.accounts = [];
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: /Income/ }));

    expect(screen.getByRole("group", { name: "Where does the money land?" })).toBeInTheDocument();
    bankAccountsStore.accounts = cards;
  });

  it("says a card below zero most likely never had its amount said, and where to say it (F24.3)", () => {
    budgetStore.summary = summary();
    const cards = bankAccountsStore.accounts;
    bankAccountsStore.accounts = [{ ...cards[0], balance: "-120.00" }];
    incomeStore.balance = { balance: "-120.00", since: null, from_accounts: true };
    renderPage();

    expect(screen.getByText("A card shows less than zero")).toBeInTheDocument();
    expect(screen.getByText(/“My card” shows -120 PLN/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Say what is on it" })).toHaveAttribute(
      "href",
      `/accounts/${String(cards[0]?.id)}`,
    );
    bankAccountsStore.accounts = cards;
    incomeStore.balance = null;
  });

  it("changes the budget in place, an empty one removing it", async () => {
    budgetStore.summary = summary({ budget_limit: "3000.00" });
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: /Budget/ }));
    fireEvent.change(screen.getByLabelText("Budget"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await vi.waitFor(() => {
      expect(profileStore.saveQuietly).toHaveBeenCalledWith({ budget_limit: null });
    });
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
