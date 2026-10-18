import { fireEvent, render, screen, within } from "@testing-library/react";
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
    photos_expire_on: null,
    ...overrides,
  };
}

const tripsStore = {
  current: null as TripDetail | null,
  loadError: null,
  loadTrip: vi.fn(),
  chooseKind: vi.fn(),
  placeReceipt: vi.fn(),
  setTimes: vi.fn(),
  isLoading: false,
  clearTimes: vi.fn(),
  clearSaveError: vi.fn(),
  isSaving: false,
  saveError: null,
};

const PHONE = {
  ...TAXI,
  id: "r2",
  merchant_name: "Apple Store",
  total_amount: "3999.00",
} as unknown as TripDetail["receipts"][number];

const exportStore = { busy: {} as Record<string, boolean>, start: vi.fn() };

vi.mock("@/stores/StoreContext", () => ({
  useStores: () => ({
    tripsStore,
    exportStore,
    receiptStore: { selectedReceiptId: null, fetchReceiptDetail: vi.fn() },
    authStore: { user: { currency: "PLN" } },
  }),
}));

function renderPage() {
  return render(
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

    // The kind also names each receipt's choice below; the tile is the one in a list item.
    const tile = (kind: string) =>
      screen
        .getAllByText(kind)
        .find((el) => el.closest("li")?.textContent.includes("PLN"))
        ?.closest("li");
    expect(tile("Transport")).toHaveTextContent("1,900 PLN");
    expect(tile("Accommodation")).toHaveTextContent("0 PLN");
    expect(tile("Meals")).toHaveTextContent("310 PLN");
    expect(tile("Other")).toHaveTextContent("630 PLN");
    expect(screen.queryByText(/converted at the NBP rate/)).not.toBeInTheDocument();
  });

  it("shows what was paid in each currency once one was foreign", () => {
    tripsStore.current = trip({
      by_currency: [
        { currency: "EGP", total: "7600.00" },
        { currency: "PLN", total: "2210.00" },
      ],
    });
    renderPage();

    expect(screen.getByText(/Paid in 7,600 EGP: converted at the NBP rate/)).toBeInTheDocument();
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

    expect(screen.getByText("2,620 PLN spent")).toBeInTheDocument();
    expect(screen.getByText("of 3,000 PLN")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "11 Oct 2026, 0 PLN" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "10 Oct 2026, 1,120 PLN" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    fireEvent.click(screen.getByRole("button", { name: /By category/ }));
    expect(screen.getByText("Dining").closest("li")).toHaveTextContent("Dining2,620.00 PLN");
  });

  it("says by how much a trip went over its budget", () => {
    tripsStore.current = trip({ total: "3100.00", budget: "3000.00", budget_left: "-100.00" });
    renderPage();

    expect(screen.getByText("100 PLN over the budget")).toBeInTheDocument();
  });

  describe("a business trip's per diem (F20.4)", () => {
    const GERMANY: TripDetail["per_diem"] = {
      departure: "2026-10-13T04:00:00Z",
      returned: "2026-10-15T19:00:00Z",
      abroad_from: null,
      abroad_to: null,
      meals: [["breakfast"], ["breakfast"], []],
      parts: [
        {
          abroad: true,
          country: "DE",
          currency: "EUR",
          rate: "49",
          total: "132.30",
          days: [1, 2].map((number) => ({
            number,
            hours: "24.00",
            share: "1",
            rule: "§ 13 ust. 3 pkt 1",
            amount: "49.00",
            meals: ["breakfast" as const],
            reduction: "7.35",
            meals_rule: "§ 14 ust. 2",
            due: "41.65",
          })),
        },
      ],
      to_pln: [{ currency: "EUR", rate: "4.25", effective_date: "2026-10-14", source: "NBP" }],
      total_pln: "562.28",
      account_currency: "PLN",
      total_account: "562.28",
      regulation: "Dz.U. 2023 poz. 2190",
    };

    it("offers to work it out before the times are given", () => {
      tripsStore.current = trip({ kind: "business", country: "DE", per_diem: null });
      renderPage();

      fireEvent.click(screen.getByRole("button", { name: "Work out the per diem" }));

      expect(screen.getByRole("dialog")).toHaveTextContent("Trip times");
      expect(screen.getAllByRole("group", { name: /Day \d/ })).toHaveLength(8);
    });

    it("shows each day with its rule, the meals taken off, and the sum in złoty", () => {
      tripsStore.current = trip({ kind: "business", country: "DE", per_diem: GERMANY });
      renderPage();

      const card = screen.getByRole("heading", { name: "Per diem" }).closest("div")?.parentElement;
      expect(card).toHaveTextContent("Abroad: Germany, 49.00 EUR a day");
      expect(card).toHaveTextContent("24.00 h · 100% · § 13 ust. 3 pkt 1");
      expect(card).toHaveTextContent("Breakfast · § 14 ust. 2 · −7.35 EUR");
      expect(card).toHaveTextContent("132.30 EUR");
      expect(card).toHaveTextContent("562.28 PLN");
      expect(card).toHaveTextContent("EUR at the NBP rate 4.2500 of 14 Oct 2026");
      expect(card).toHaveTextContent("Under the regulation Dz.U. 2023 poz. 2190");
    });

    it("sends the times and the meals ticked for each day", () => {
      tripsStore.current = trip({ kind: "business", country: "DE", per_diem: GERMANY });
      tripsStore.setTimes.mockResolvedValue(true);
      renderPage();
      fireEvent.click(screen.getByRole("button", { name: "Change times" }));

      const thirdDay = screen.getByRole("group", { name: "Day 3" });
      fireEvent.click(within(thirdDay).getByRole("button", { name: "Dinner" }));
      fireEvent.click(screen.getByRole("button", { name: "Work out" }));

      expect(tripsStore.setTimes).toHaveBeenCalledWith(
        "t1",
        expect.objectContaining({
          departure: "2026-10-13T04:00:00.000Z",
          returned: "2026-10-15T19:00:00.000Z",
          abroad_from: null,
          meals: [["breakfast"], ["breakfast"], ["dinner"]],
        }),
      );
    });
  });

  describe("a business trip's settlement (F20.5)", () => {
    const SETTLEMENT = {
      currency: "PLN",
      expenses: "612.40",
      per_diem: "207.00",
      advance: "500.00",
      to_reimburse: "319.40",
    };

    it("adds expenses and per diem up and takes the advance off", () => {
      tripsStore.current = trip({ kind: "business", settlement: SETTLEMENT });
      renderPage();

      const card = screen.getByRole("heading", { name: "Settlement" }).parentElement;
      expect(card).toHaveTextContent("Expenses612.40 PLN");
      expect(card).toHaveTextContent("Per diem+ 207.00 PLN");
      expect(card).toHaveTextContent("Advance− 500.00 PLN");
      expect(card).toHaveTextContent("To reimburse319.40 PLN");
    });

    it("says what goes back to the employer when the advance was more", () => {
      tripsStore.current = trip({
        kind: "business",
        settlement: { ...SETTLEMENT, to_reimburse: "-80.00" },
      });
      renderPage();

      expect(screen.getByText("To return to the employer")).toBeInTheDocument();
      expect(screen.getByText("80.00 PLN")).toBeInTheDocument();
    });

    it("downloads the settlement as a PDF with the photos, or as CSV", () => {
      tripsStore.current = trip({ kind: "business", settlement: SETTLEMENT });
      renderPage();

      fireEvent.click(screen.getByRole("button", { name: /PDF with photos/ }));
      fireEvent.click(screen.getByRole("button", { name: /CSV/ }));

      expect(exportStore.start).toHaveBeenCalledWith(
        expect.objectContaining({ kind: "trip", format: "pdf", trip_id: "t1" }),
      );
      expect(exportStore.start).toHaveBeenLastCalledWith(
        expect.objectContaining({ kind: "trip", format: "csv", trip_id: "t1" }),
      );
    });

    it("warns before the trip's photos are removed, and not long before (F17.9.3)", () => {
      const inDays = (days: number) =>
        new Date(Date.now() + days * 86_400_000).toISOString().slice(0, 10);
      tripsStore.current = trip({
        kind: "business",
        settlement: SETTLEMENT,
        photos_expire_on: inDays(10),
      });
      const { unmount } = renderPage();
      expect(screen.getByText(/Receipt photos are kept 90 days/)).toBeInTheDocument();
      unmount();

      tripsStore.current = trip({
        kind: "business",
        settlement: SETTLEMENT,
        photos_expire_on: inDays(80),
      });
      renderPage();
      expect(screen.queryByText(/Receipt photos are kept 90 days/)).not.toBeInTheDocument();
    });
  });
});
