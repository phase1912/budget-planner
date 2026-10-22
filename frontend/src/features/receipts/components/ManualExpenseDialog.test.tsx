import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Trip } from "@/stores/TripsStore";
import { ManualExpenseDialog } from "./ManualExpenseDialog";

const BERLIN: Trip = {
  id: "t1",
  kind: "business",
  name: "Berlin",
  country: "DE",
  city: null,
  start_date: "2026-10-13",
  end_date: "2026-10-15",
  purpose: null,
  receipt_count: 0,
  total: "0",
  asking_count: 0,
};

const stores = vi.hoisted(() => ({
  receiptStore: { addManualExpense: vi.fn() },
  categoriesStore: {
    assignableBuiltIns: [
      { id: "c-other", name: "Other", is_builtin: true },
      { id: "c-fun", name: "Entertainment", is_builtin: true },
    ],
    customCategories: [],
    ensureCategories: vi.fn(),
  },
  tripsStore: { trips: [] as unknown[], load: vi.fn() },
  authStore: { user: { currency: "PLN" } },
}));

vi.mock("@/stores/StoreContext", () => ({ useStores: () => stores }));

function fill(date: string) {
  fireEvent.change(screen.getByLabelText("What was it"), { target: { value: "Pyramids tour" } });
  fireEvent.change(screen.getByLabelText("Date"), { target: { value: date } });
  fireEvent.change(screen.getByLabelText("Amount"), { target: { value: "120,00" } });
}

describe("ManualExpenseDialog (F20.5)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    stores.tripsStore.trips = [BERLIN];
    stores.receiptStore.addManualExpense.mockResolvedValue(true);
  });

  it("records an expense with no receipt, in the account's currency, under Other", () => {
    render(<ManualExpenseDialog onClose={vi.fn()} />);
    fill("2026-10-03");

    expect(screen.queryByLabelText("On a trip, it was")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Add expense" }));

    expect(stores.receiptStore.addManualExpense).toHaveBeenCalledWith({
      description: "Pyramids tour",
      spent_on: "2026-10-03",
      amount: "120.00",
      currency: null,
      category_id: "c-other",
      kind: null,
      trip_chosen: false,
      trip_id: null,
    });
  });

  it("asks whether an expense on a business trip is the company's before adding it", () => {
    render(<ManualExpenseDialog onClose={vi.fn()} />);
    fill("2026-10-14");

    expect(screen.getByText("Is this a business expense on «Berlin»?")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add expense" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "No, my own" }));
    expect(screen.queryByLabelText("On a trip, it was")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Add expense" }));

    expect(stores.receiptStore.addManualExpense).toHaveBeenCalledWith(
      expect.objectContaining({ trip_chosen: true, trip_id: null }),
    );
  });

  it("asks what part of the trip it was only once the expense goes into the trip", () => {
    render(<ManualExpenseDialog onClose={vi.fn()} />);
    fill("2026-10-14");
    fireEvent.click(screen.getByRole("button", { name: "Yes, the company pays" }));
    fireEvent.change(screen.getByLabelText("On a trip, it was"), {
      target: { value: "transport" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add expense" }));

    expect(stores.receiptStore.addManualExpense).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "transport", trip_chosen: true, trip_id: "t1" }),
    );
  });

  it("puts an expense added on a trip's page into that trip without asking", () => {
    render(<ManualExpenseDialog fromTrip={BERLIN} onClose={vi.fn()} />);
    fill("2026-10-14");

    expect(screen.queryByRole("button", { name: "No, my own" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Add expense" }));

    expect(stores.receiptStore.addManualExpense).toHaveBeenCalledWith(
      expect.objectContaining({ trip_chosen: true, trip_id: "t1" }),
    );
  });
});
