import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RegularIncomes } from "./RegularIncomes";

const stores = vi.hoisted(() => ({
  authStore: { user: { currency: "PLN", pays_own_taxes: false } },
  bankAccountsStore: {
    accounts: [],
    loaded: true,
    any: true,
    load: vi.fn(),
    byId: () => undefined,
    saveState: { isLoading: false },
  },
  householdStore: {
    household: null as { id: string } | null,
    get mayShare() {
      return this.household !== null;
    },
    isChild: false,
    loaded: true,
    load: vi.fn(),
  },
  incomeStore: {
    regular: [] as {
      id: string;
      name: string;
      amount: string;
      day: number | null;
      taxed: boolean;
      starts_on: string;
    }[],
    bills: [] as Record<string, unknown>[],
    loadRegular: vi.fn(),
    loadBills: vi.fn(),
    addBill: vi.fn().mockResolvedValue(true),
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
    stores.incomeStore.bills = [];
    stores.householdStore.household = null;
  });

  it("in a family, shares a new bill by default, whole and never divided (F12.8)", async () => {
    stores.householdStore.household = { id: "h1" };
    stores.incomeStore.bills = [
      {
        id: "b1",
        name: "Flat",
        amount: "3000.00",
        day: 5,
        starts_on: "2026-10-01",
        shared: true,
        mine: false,
        added_by: "Anna",
      },
    ];
    render(<RegularIncomes kind="bill" />);

    expect(screen.getByText("Shared")).toBeInTheDocument();
    expect(screen.getByText(/added by Anna/)).toBeInTheDocument();
    expect(screen.queryByText(/your part/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Add another bill" }));
    expect(screen.getByRole("radio", { name: "Shared with family" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(screen.queryByRole("radio", { name: "By income" })).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("What it is"), { target: { value: "Internet" } });
    fireEvent.change(screen.getByLabelText("Each time, PLN"), { target: { value: "69" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(stores.incomeStore.addBill).toHaveBeenCalledWith(
        {
          name: "Internet",
          amount: "69",
          day: null,
          weekday: null,
          shared: true,
          account_id: null,
        },
        expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
      );
    });
  });

  it("adds a regular income, counted from this month", async () => {
    render(<RegularIncomes />);

    fireEvent.click(screen.getByRole("button", { name: "Add a regular income" }));
    fireEvent.change(screen.getByLabelText("What it is"), { target: { value: "Salary" } });
    fireEvent.change(screen.getByLabelText("Each time, PLN"), { target: { value: "10 000" } });
    fireEvent.change(screen.getByLabelText("Day of the month"), { target: { value: "10" } });
    expect(screen.queryByRole("switch")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(stores.incomeStore.addRegular).toHaveBeenCalledWith(
        {
          name: "Salary",
          amount: "10000",
          day: 10,
          weekday: null,
          taxed: false,
          shared: false,
          account_id: null,
          about: false,
          // No card yet: income makes the one it lands on (F23.21).
          new_card: { name: "My card", opening: "0" },
        },
        expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
      );
    });
  });

  it("lets a step's Next save a typed income, drop a blank one and hold a half one (F24.3)", async () => {
    let finish: (() => Promise<boolean>) | null = null;
    render(
      <RegularIncomes
        onPending={(f) => {
          finish = f;
        }}
      />,
    );
    const run = async () => {
      let done = false;
      await act(async () => {
        done = await (finish as unknown as () => Promise<boolean>)();
      });
      return done;
    };

    fireEvent.click(screen.getByRole("button", { name: "Add a regular income" }));
    expect(await run()).toBe(true);
    expect(stores.incomeStore.addRegular).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Add a regular income" }));
    fireEvent.change(screen.getByLabelText("What it is"), { target: { value: "Salary" } });
    expect(await run()).toBe(false);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Fill in what it is and how much, or cancel it.",
    );

    fireEvent.change(screen.getByLabelText("Each time, PLN"), { target: { value: "1000" } });
    expect(await run()).toBe(true);
    expect(stores.incomeStore.addRegular).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Salary", amount: "1000" }),
      expect.any(String),
    );
    // The card that income made is listed at once (the onboarding summary reads it).
    expect(stores.bankAccountsStore.load).toHaveBeenCalled();
  });

  it("adds a bill that comes every week on its weekday, needing no card (F23.21)", async () => {
    render(<RegularIncomes kind="bill" />);

    fireEvent.click(screen.getByRole("button", { name: /Add .*bill/ }));
    fireEvent.change(screen.getByLabelText(/What it is|Name/), { target: { value: "Gym" } });
    fireEvent.change(screen.getByLabelText("Each time, PLN"), { target: { value: "50" } });
    fireEvent.click(screen.getByRole("button", { name: "Weekly" }));
    fireEvent.change(screen.getByLabelText("Day of the week"), { target: { value: "0" } });
    expect(screen.queryByText("Where does the money land?")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(stores.incomeStore.addBill).toHaveBeenCalledWith(
        expect.objectContaining({ name: "Gym", day: null, weekday: 0 }),
        expect.any(String),
      );
    });
  });

  it("asks one who pays their own taxes whether the tax comes out of it", async () => {
    stores.authStore.user.pays_own_taxes = true;
    render(<RegularIncomes />);

    fireEvent.click(screen.getByRole("button", { name: "Add a regular income" }));
    fireEvent.change(screen.getByLabelText("What it is"), { target: { value: "B2B" } });
    fireEvent.change(screen.getByLabelText("Each time, PLN"), { target: { value: "20000" } });
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
    fireEvent.change(screen.getByLabelText("Each time, PLN"), { target: { value: "11000" } });
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
