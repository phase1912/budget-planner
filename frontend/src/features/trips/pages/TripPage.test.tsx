import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { TripDetail } from "@/stores/TripsStore";
import { TripPage } from "./TripPage";

vi.mock("@/features/receipts/components/ReceiptDetailModal", () => ({
  ReceiptDetailModal: () => null,
}));

const TAXI = {
  id: "r1",
  user_id: "me",
  merchant_name: "Cairo Taxi",
  transaction_date: "2026-10-02T09:00:00Z",
  created_at: "2026-10-02T09:00:00Z",
  total_amount: "45.00",
  status: "parsed",
  channel: "photo",
  is_private: false,
  expense_kind: "other",
  expense_kind_chosen: false,
} as unknown as TripDetail["receipts"][number];

function trip(overrides: Partial<TripDetail> = {}): TripDetail {
  return {
    id: "t1",
    kind: "personal",
    name: "Egypt",
    country: "EG",
    city: null,
    start_date: "2026-10-01",
    end_date: "2026-10-08",
    purpose: null,
    receipt_count: 1,
    total: "2840.00",
    asking_count: 0,
    budget: null,
    budget_left: null,
    days: [{ day: "2026-10-02", total: "2840.00" }],
    categories: [{ category: "Transport", total: "2840.00" }],
    receipts: [TAXI],
    asking: [],
    by_kind: [
      { kind: "transport", total: "1900.00" },
      { kind: "accommodation", total: "0.00" },
      { kind: "meals", total: "310.00" },
      { kind: "other", total: "630.00" },
    ],
    by_currency: [{ currency: "PLN", total: "2840.00" }],
    ...overrides,
  };
}

const tripsStore = {
  current: null as TripDetail | null,
  loadError: null,
  loadTrip: vi.fn(),
  chooseKind: vi.fn(),
  placeReceipt: vi.fn(),
};

const PHONE = {
  ...TAXI,
  id: "r2",
  merchant_name: "Apple Store",
  total_amount: "3999.00",
} as unknown as TripDetail["receipts"][number];

vi.mock("@/stores/StoreContext", () => ({
  useStores: () => ({
    tripsStore,
    receiptStore: { selectedReceiptId: null, fetchReceiptDetail: vi.fn() },
    authStore: { user: { currency: "PLN" } },
  }),
}));

function renderPage() {
  render(
    <MemoryRouter initialEntries={["/trips/t1"]}>
      <Routes>
        <Route path="/trips/:id" element={<TripPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("TripPage — what a trip cost, by kind (F20.2)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    tripsStore.current = trip();
  });

  it("lists every kind, a zero one too, in the account's currency", () => {
    renderPage();

    const kinds = screen.getByRole("heading", { name: "By kind" }).parentElement;
    expect(kinds).toHaveTextContent("Transport1,900.00 PLN");
    expect(kinds).toHaveTextContent("Accommodation0.00 PLN");
    expect(kinds).toHaveTextContent("Meals310.00 PLN");
    expect(kinds).toHaveTextContent("Other630.00 PLN");
    expect(screen.queryByText("Paid in:")).not.toBeInTheDocument();
  });

  it("shows what was paid in each currency once one was foreign", () => {
    tripsStore.current = trip({
      by_currency: [
        { currency: "EGP", total: "7600.00" },
        { currency: "PLN", total: "2210.00" },
      ],
    });
    renderPage();

    expect(screen.getByText("Paid in:")).toBeInTheDocument();
    expect(screen.getByText("7,600.00 EGP")).toBeInTheDocument();
    expect(screen.getByText("2,210.00 PLN")).toBeInTheDocument();
  });

  it("moves a receipt to another kind in place", () => {
    renderPage();
    const kind = screen.getByRole("combobox", { name: "What Cairo Taxi paid for" });
    expect(kind).toHaveValue("other");

    fireEvent.change(kind, { target: { value: "transport" } });

    expect(tripsStore.chooseKind).toHaveBeenCalledWith("r1", "transport");
  });

  it("asks a business trip's question about each receipt from its days", () => {
    tripsStore.current = trip({ kind: "business", name: "Berlin", asking: [PHONE] });
    renderPage();

    expect(
      screen.getByRole("heading", { name: "Receipts from these days — business?" }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "No, my own" }));
    expect(tripsStore.placeReceipt).toHaveBeenCalledWith("r2", null);
    fireEvent.click(screen.getByRole("button", { name: "Yes, the company pays" }));
    expect(tripsStore.placeReceipt).toHaveBeenLastCalledWith("r2", "t1");
  });

  it("offers to upload a receipt straight into the trip", () => {
    renderPage();
    expect(screen.getByRole("link", { name: "Add receipt" })).toHaveAttribute(
      "href",
      "/upload?trip=t1",
    );
  });

  it("reads a personal trip against its budget, day by day and by category (F20.3)", () => {
    tripsStore.current = trip({
      total: "2620.00",
      budget: "3000.00",
      budget_left: "380.00",
      days: [
        { day: "2026-10-10", total: "1120.00" },
        { day: "2026-10-11", total: "0.00" },
      ],
      categories: [{ category: "Dining", total: "2620.00" }],
    });
    renderPage();

    expect(screen.getByText("87% of 3,000.00 PLN")).toBeInTheDocument();
    expect(screen.getByText("380.00 PLN left")).toBeInTheDocument();
    const days = screen.getByRole("heading", { name: "Day by day" }).parentElement;
    expect(days).toHaveTextContent("10 Oct 2026");
    expect(days).toHaveTextContent("0.00 PLN");
    const categories = screen.getByRole("heading", { name: "By category" }).parentElement;
    expect(categories).toHaveTextContent("Dining2,620.00 PLN");
  });

  it("says by how much a trip went over its budget", () => {
    tripsStore.current = trip({ total: "3100.00", budget: "3000.00", budget_left: "-100.00" });
    renderPage();

    expect(screen.getByText("100.00 PLN over")).toBeInTheDocument();
  });
});
