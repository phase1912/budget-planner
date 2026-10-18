import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RegularIncomes } from "./RegularIncomes";

const stores = vi.hoisted(() => ({
  authStore: { user: { currency: "PLN", pays_own_taxes: false } },
  incomeStore: {
    regular: [] as {
      id: string;
      name: string;
      amount: string;
      day: number | null;
      taxed: boolean;
      starts_on: string;
    }[],
    loadRegular: vi.fn(),
    addRegular: vi.fn().mockResolvedValue(true),
    changeRegular: vi.fn().mockResolvedValue(true),
    endRegular: vi.fn().mockResolvedValue(true),
  },
}));

vi.mock("@/stores/StoreContext", () => ({ useStores: () => stores }));

describe("RegularIncomes (F23.17)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    stores.authStore.user.pays_own_taxes = false;
    stores.incomeStore.regular = [];
  });

  it("adds a regular income, counted from this month", async () => {
    render(<RegularIncomes />);

    fireEvent.click(screen.getByRole("button", { name: "Add a regular income" }));
    fireEvent.change(screen.getByLabelText("What it is"), { target: { value: "Salary" } });
    fireEvent.change(screen.getByLabelText("A month, PLN"), { target: { value: "10 000" } });
    fireEvent.change(screen.getByLabelText("Comes on"), { target: { value: "10" } });
    expect(screen.queryByRole("switch")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(stores.incomeStore.addRegular).toHaveBeenCalledWith(
        { name: "Salary", amount: "10000", day: 10, taxed: false },
        expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
      );
    });
  });

  it("asks one who pays their own taxes whether the tax comes out of it", async () => {
    stores.authStore.user.pays_own_taxes = true;
    render(<RegularIncomes />);

    fireEvent.click(screen.getByRole("button", { name: "Add a regular income" }));
    fireEvent.change(screen.getByLabelText("What it is"), { target: { value: "B2B" } });
    fireEvent.change(screen.getByLabelText("A month, PLN"), { target: { value: "20000" } });
    fireEvent.click(screen.getByRole("switch", { name: "My tax comes out of it" }));
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(stores.incomeStore.addRegular).toHaveBeenCalledWith(
        expect.objectContaining({ name: "B2B", taxed: true }),
        expect.any(String),
      );
    });
  });

  it("changes one, and stops one from next month", async () => {
    stores.incomeStore.regular = [
      {
        id: "r1",
        name: "Salary",
        amount: "10000.00",
        day: 10,
        taxed: false,
        starts_on: "2026-09-01",
      },
    ];
    render(<RegularIncomes />);

    expect(screen.getByText("on day 10")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Salary/ }));
    fireEvent.change(screen.getByLabelText("A month, PLN"), { target: { value: "11000" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => {
      expect(stores.incomeStore.changeRegular).toHaveBeenCalledWith(
        "r1",
        expect.objectContaining({ amount: "11000" }),
      );
    });

    fireEvent.click(screen.getByRole("button", { name: /Salary/ }));
    fireEvent.click(screen.getByRole("button", { name: "Stop it" }));
    await waitFor(() => {
      expect(stores.incomeStore.endRegular).toHaveBeenCalledWith("r1", expect.any(String));
    });
  });
});
