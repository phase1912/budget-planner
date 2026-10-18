import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PlanPage } from "./PlanPage";

const stores = vi.hoisted(() => ({
  authStore: {
    user: {
      currency: "PLN",
      budget_limit: "3000.00",
      usual_income: "6800.00",
      travels_for_work: false,
      pays_own_taxes: false,
    },
  },
  incomeStore: {
    month: {
      total: "6200.00",
      entered: true,
      regular: [] as { id: string; name: string; amount: string; taxed: boolean }[],
      entries: [
        {
          id: "i1",
          received_on: "2026-10-10",
          amount: "6200.00",
          source: "ACME",
          kind: "salary",
          channel: "manual",
        },
      ],
    },
    saveState: { isLoading: false },
    load: vi.fn(),
    loadBalance: vi.fn(),
    payTaxes: vi.fn().mockResolvedValue(true),
    add: vi.fn().mockResolvedValue(true),
    update: vi.fn().mockResolvedValue(true),
    remove: vi.fn().mockResolvedValue(true),
  },
  budgetStore: {
    current: { year: 2026, month: 10 },
    summary: { month: 10, total: "1800.00" },
    today: "2026-10-17",
    open: vi.fn(),
  },
  tripsStore: {
    trips: [
      {
        id: "t1",
        kind: "personal",
        name: "Crete",
        start_date: "2026-06-03",
        end_date: "2026-06-14",
        total: "1555.00",
        budget: "4000.00",
        budget_left: "2445.00",
      },
      {
        id: "t2",
        kind: "business",
        name: "Berlin",
        start_date: "2026-09-01",
        end_date: "2026-09-03",
        total: "300",
      },
    ],
    load: vi.fn(),
  },
  goalsStore: {
    goals: [{ id: "g1", name: "Greece", type: "financial", target_amount: "8000.00" }],
    load: vi.fn(),
  },
  profileStore: { saveQuietly: vi.fn().mockResolvedValue(true) },
}));

vi.mock("@/stores/StoreContext", () => ({ useStores: () => stores }));

const renderPage = () =>
  render(
    <MemoryRouter>
      <PlanPage />
    </MemoryRouter>,
  );

describe("PlanPage (F23.2, F23.10, F23.12)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    stores.authStore.user.travels_for_work = false;
    stores.authStore.user.pays_own_taxes = false;
  });

  it("shows one who pays their own taxes what came in, the taxes, and what is theirs", async () => {
    stores.authStore.user.pays_own_taxes = true;
    const month = stores.incomeStore.month as Record<string, unknown>;
    Object.assign(month, { taxes: "2344.00", net: "3856.00", taxes_paid: "0.00" });
    renderPage();

    expect(screen.getByText("Came in")).toBeInTheDocument();
    expect(screen.getByText("2,344")).toBeInTheDocument();
    expect(screen.getByText("3,856")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "I paid taxes" }));
    expect(screen.getByLabelText("Paid")).toHaveValue("2344.00");
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await vi.waitFor(() => {
      expect(stores.incomeStore.payTaxes).toHaveBeenCalledWith("2344.00", "2026-10-17", {
        year: 2026,
        month: 10,
      });
    });
    Object.assign(month, { taxes: undefined, net: undefined, taxes_paid: undefined });
  });

  it("lets an income be marked as untaxed when it is a gift", async () => {
    stores.authStore.user.pays_own_taxes = true;
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Add income" }));
    fireEvent.change(screen.getByLabelText("Amount"), { target: { value: "1000" } });
    expect(screen.getByRole("switch", { name: "I pay tax on this" })).toBeChecked();
    fireEvent.click(screen.getByRole("switch", { name: "I pay tax on this" }));
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await vi.waitFor(() => {
      expect(stores.incomeStore.add).toHaveBeenCalledWith(
        expect.objectContaining({ amount: "1000", taxed: false }),
      );
    });
  });

  it("shows the month's income, the budget, holidays and goals", () => {
    renderPage();

    expect(screen.getAllByText("6,200 PLN")).toHaveLength(2);
    expect(screen.getByText(/Usual: 6,800 PLN a month/)).toBeInTheDocument();
    expect(screen.getByText("1,800 of 3,000 PLN spent")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Crete/ })).toHaveAttribute("href", "/trips/t1");
    expect(screen.getByText("2,445 PLN left")).toBeInTheDocument();
    expect(screen.queryByText("Berlin")).not.toBeInTheDocument();
    expect(screen.getByText("Greece")).toBeInTheDocument();
  });

  it("shows business trips only to someone who travels for work", () => {
    stores.authStore.user.travels_for_work = true;
    renderPage();
    expect(screen.getByRole("link", { name: /Business trips/ })).toHaveAttribute(
      "href",
      "/trips?kind=business",
    );
  });

  it("adds an income entry by hand", async () => {
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Add income" }));
    fireEvent.change(screen.getByLabelText("Amount"), { target: { value: "600" } });
    fireEvent.change(screen.getByLabelText("From"), { target: { value: "Side project" } });
    fireEvent.change(screen.getByLabelText("Kind"), { target: { value: "side" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await vi.waitFor(() => {
      expect(stores.incomeStore.add).toHaveBeenCalledWith({
        received_on: "2026-10-17",
        amount: "600",
        source: "Side project",
        kind: "side",
      });
    });
  });

  it("changes or deletes an entry from its row", async () => {
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: /ACME/ }));
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));

    await vi.waitFor(() => {
      expect(stores.incomeStore.remove).toHaveBeenCalledWith("i1");
    });
  });
});
