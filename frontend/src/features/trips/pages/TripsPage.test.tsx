import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Trip, TripSuggestion } from "@/stores/TripsStore";
import { TripsPage } from "./TripsPage";

const SUGGESTION: TripSuggestion = {
  start: "2026-08-03",
  end: "2026-08-09",
  currency: "EUR",
  receipts: 5,
  amount: "214.30",
};

const tripsStore = {
  trips: [] as Trip[],
  openSuggestions: [] as TripSuggestion[],
  isLoading: false,
  isSaving: false,
  loadError: null as string | null,
  saveError: null as string | null,
  load: vi.fn(),
  save: vi.fn(),
  dismissSuggestion: vi.fn(),
  clearSaveError: vi.fn(),
};

vi.mock("@/stores/StoreContext", () => ({
  useStores: () => ({ tripsStore, authStore: { user: { currency: "PLN" } } }),
}));

function renderPage() {
  render(
    <MemoryRouter>
      <TripsPage />
    </MemoryRouter>,
  );
}

describe("TripsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.assign(tripsStore, { trips: [], openSuggestions: [], loadError: null });
  });

  it("lists each trip with its receipts and what it cost, opening to its page", () => {
    tripsStore.trips = [
      {
        id: "t1",
        kind: "business",
        name: "Berlin",
        country: "DE",
        city: "Berlin",
        start_date: "2026-09-14",
        end_date: "2026-09-17",
        purpose: "Conference",
        receipt_count: 3,
        total: "312.40",
        asking_count: 2,
      },
    ];
    renderPage();

    expect(tripsStore.load).toHaveBeenCalled();
    const card = screen.getByRole("link", { name: /Berlin/ });
    expect(card).toHaveAttribute("href", "/trips/t1");
    expect(card).toHaveTextContent("Business");
    expect(card).toHaveTextContent("3 receipts");
    expect(card).toHaveTextContent("312.40 PLN");
    expect(card).toHaveTextContent("2 receipts wait for an answer");
  });

  it("says there are no trips yet", () => {
    renderPage();
    expect(screen.getByText(/No trips yet/)).toBeInTheDocument();
  });

  it("offers a run of foreign-currency receipts as a trip, prefilled with its dates", () => {
    tripsStore.openSuggestions = [SUGGESTION];
    renderPage();

    expect(screen.getByText("Looks like a trip")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Record trip" }));

    expect(screen.getByLabelText("From")).toHaveValue("2026-08-03");
    expect(screen.getByLabelText("To")).toHaveValue("2026-08-09");
  });

  it("sets a suggestion aside when it is not a trip", () => {
    tripsStore.openSuggestions = [SUGGESTION];
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Not a trip" }));

    expect(tripsStore.dismissSuggestion).toHaveBeenCalledWith(SUGGESTION);
  });

  it("will not save a trip that ends before it starts", () => {
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "New trip" }));
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Egypt" } });
    fireEvent.change(screen.getByLabelText("From"), { target: { value: "2026-08-09" } });
    fireEvent.change(screen.getByLabelText("To"), { target: { value: "2026-08-03" } });

    expect(screen.getByText("The trip cannot end before it starts.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save trip" })).toBeDisabled();
  });

  it("asks a business trip its purpose and sends it", () => {
    tripsStore.save.mockResolvedValue("t9");
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "New trip" }));
    fireEvent.click(screen.getByRole("button", { name: "Business" }));
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Berlin" } });
    fireEvent.change(screen.getByLabelText("From"), { target: { value: "2026-09-14" } });
    fireEvent.change(screen.getByLabelText("To"), { target: { value: "2026-09-17" } });
    fireEvent.change(screen.getByLabelText("Purpose"), { target: { value: "Conference" } });
    fireEvent.click(screen.getByRole("button", { name: "Save trip" }));

    expect(tripsStore.save).toHaveBeenCalledWith(
      {
        kind: "business",
        name: "Berlin",
        country: null,
        city: null,
        start_date: "2026-09-14",
        end_date: "2026-09-17",
        purpose: "Conference",
        budget: null,
        advance: null,
        advance_paid_on: null,
      },
      undefined,
    );
  });

  it("gives a personal trip a budget and checks it is an amount (F20.3)", () => {
    tripsStore.save.mockResolvedValue("t9");
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "New trip" }));
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Mountains" } });
    fireEvent.change(screen.getByLabelText("From"), { target: { value: "2026-10-10" } });
    fireEvent.change(screen.getByLabelText("To"), { target: { value: "2026-10-12" } });
    const budget = screen.getByLabelText("Budget, PLN");

    fireEvent.change(budget, { target: { value: "abc" } });
    expect(screen.getByText("Enter an amount above zero.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save trip" })).toBeDisabled();

    fireEvent.change(budget, { target: { value: "3000,50" } });
    fireEvent.click(screen.getByRole("button", { name: "Save trip" }));

    expect(tripsStore.save).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "personal", budget: "3000.50" }),
      undefined,
    );
  });

  it("records the advance a business trip was paid, and when (F20.5)", () => {
    tripsStore.save.mockResolvedValue("t9");
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "New trip" }));
    fireEvent.click(screen.getByRole("button", { name: "Business" }));
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Berlin" } });
    fireEvent.change(screen.getByLabelText("From"), { target: { value: "2026-10-13" } });
    fireEvent.change(screen.getByLabelText("To"), { target: { value: "2026-10-15" } });
    fireEvent.change(screen.getByLabelText("Advance received, PLN"), {
      target: { value: "500,00" },
    });
    fireEvent.change(screen.getByLabelText("Paid on"), { target: { value: "2026-10-10" } });
    fireEvent.click(screen.getByRole("button", { name: "Save trip" }));

    expect(tripsStore.save).toHaveBeenCalledWith(
      expect.objectContaining({ advance: "500.00", advance_paid_on: "2026-10-10", budget: null }),
      undefined,
    );
  });
});
