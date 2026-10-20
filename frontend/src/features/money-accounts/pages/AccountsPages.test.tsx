import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/api/client";
import { RootStore } from "@/stores/RootStore";
import type { BankAccount } from "@/stores/BankAccountsStore";
import type { Household } from "@/stores/HouseholdStore";
import { StoreProvider } from "@/stores/StoreContext";
import { AccountPage } from "./AccountPage";
import { AccountsPage } from "./AccountsPage";

vi.mock("@/api/client", () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), use: vi.fn() },
}));

type Call = (path: string, options?: unknown) => Promise<unknown>;
const api = apiClient as unknown as Record<
  "GET" | "POST" | "PUT" | "DELETE",
  ReturnType<typeof vi.fn<Call>>
>;

const account = (fields: Partial<BankAccount>): BankAccount => ({
  id: "a1",
  name: "Our card",
  kind: "personal",
  opening: "0",
  opening_on: "2026-10-01",
  tax_rate: null,
  for_purchases: true,
  balance: "8300.00",
  set_aside: "0",
  shared: true,
  mine: true,
  added_by: null,
  ...fields,
});

const BUSINESS = account({
  id: "b1",
  name: "Business",
  kind: "business",
  tax_rate: "5.00",
  for_purchases: false,
  balance: "30000.00",
  set_aside: "1780.00",
});
const DEPOSIT = account({
  id: "d1",
  name: "Deposit",
  kind: "deposit",
  shared: false,
  balance: "9000.00",
});

const FAMILY: Household = {
  id: "h1",
  name: "Home",
  my_role: "owner",
  owner_sets_budget: false,
  members: [
    {
      user_id: "me",
      first_name: "Bohdan",
      last_name: "R",
      email: "b@x",
      role: "owner",
      joined_at: "",
    },
    {
      user_id: "anna",
      first_name: "Anna",
      last_name: "R",
      email: "a@x",
      role: "member",
      joined_at: "",
    },
  ],
};

const HISTORY = {
  account: BUSINESS,
  month: "2026-10",
  closed: false,
  entries: [
    {
      day: "2026-10-20",
      kind: "bill",
      name: "ZUS",
      amount: "-1600.00",
      tax: "0",
      by_rule: true,
      upcoming: true,
      count: 0,
      author: null,
      ref: "bill",
      ref_id: "z1",
      editable: true,
    },
    {
      day: "2026-10-15",
      kind: "income",
      name: "Acme",
      amount: "12000.00",
      tax: "600.00",
      by_rule: false,
      upcoming: false,
      count: 0,
      author: null,
      ref: "income",
      ref_id: "i1",
      editable: true,
    },
  ],
};

function respond(store: RootStore) {
  api.GET.mockImplementation((path: string) =>
    Promise.resolve({
      data:
        path === "/api/v1/accounts"
          ? {
              accounts: [account({}), BUSINESS, DEPOSIT],
              total: "47300.00",
              set_aside: "1780.00",
            }
          : path.endsWith("/history")
            ? HISTORY
            : path === "/api/v1/household"
              ? store.householdStore.household
              : [],
    }),
  );
}

function renderAt(store: RootStore, url: string) {
  return render(
    <StoreProvider store={store}>
      <MemoryRouter initialEntries={[url]}>
        <Routes>
          <Route path="/accounts" element={<AccountsPage />} />
          <Route path="/accounts/:id" element={<AccountPage />} />
        </Routes>
      </MemoryRouter>
    </StoreProvider>,
  );
}

describe("accounts (F23.15)", () => {
  let store: RootStore;

  beforeEach(() => {
    vi.clearAllMocks();
    store = new RootStore();
    store.authStore.user = { id: "me", currency: "PLN" } as typeof store.authStore.user;
    store.householdStore.household = FAMILY;
    store.householdStore.loaded = true;
    respond(store);
  });

  it("show where the money is, together and what of it is the tax office's", async () => {
    renderAt(store, "/accounts");

    expect(await screen.findByText("47,300 PLN")).toBeInTheDocument();
    expect(screen.getByText("Of it 1,780 PLN set aside for taxes")).toBeInTheDocument();
    expect(screen.getByText(/Business · tax 5%/)).toBeInTheDocument();
    expect(screen.getByText(/Deposit · just the amount for now/)).toBeInTheDocument();
  });

  it("count only the shared ones when asked", async () => {
    renderAt(store, "/accounts");
    await screen.findByText("47,300 PLN");

    fireEvent.click(screen.getByRole("button", { name: "Shared" }));

    expect(screen.getByText("On shared accounts")).toBeInTheDocument();
    expect(screen.getByText("38,300 PLN")).toBeInTheDocument();
    expect(screen.queryByText("Deposit")).not.toBeInTheDocument();
  });

  it("offer to add the first one when there is none", async () => {
    api.GET.mockImplementation((path: string) =>
      Promise.resolve({
        data: path === "/api/v1/accounts" ? { accounts: [], total: "0", set_aside: "0" } : [],
      }),
    );
    renderAt(store, "/accounts");

    expect(await screen.findByText("Keep track of where the money is")).toBeInTheDocument();
  });

  it("show an account's month with the tax set aside and what is still to come", async () => {
    renderAt(store, "/accounts/b1");

    expect(
      await screen.findByText("Tax: 5% of each payment in · 1,780 PLN set aside"),
    ).toBeInTheDocument();
    const history = screen.getByRole("region", { name: "History" });
    expect(within(history).getByText(/from outside · tax 600 set aside/)).toBeInTheDocument();
    expect(within(history).getByText(/bill · by the rule · upcoming/)).toBeInTheDocument();
  });

  it("set the business rate aside of money from outside before it is saved", async () => {
    api.POST.mockResolvedValue({ data: undefined });
    renderAt(store, "/accounts/b1");

    fireEvent.click(await screen.findByRole("button", { name: "Money in" }));
    fireEvent.change(screen.getByLabelText("From whom"), { target: { value: "Acme" } });
    fireEvent.change(screen.getByLabelText("Amount, PLN"), { target: { value: "10 000" } });

    expect(screen.getByText("−500 PLN")).toBeInTheDocument();
    expect(screen.getByText("9,500 PLN")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => {
      expect(api.POST).toHaveBeenCalledWith(
        "/api/v1/accounts/{account_id}/money-in",
        expect.objectContaining({
          body: expect.objectContaining({
            amount: "10000",
            source: "Acme",
            from_account_id: null,
          }) as unknown,
        }),
      );
    });
  });

  it("let a child look at a shared account without changing it (F12.10)", async () => {
    store.householdStore.household = { ...FAMILY, my_role: "child" };
    renderAt(store, "/accounts/b1");

    expect(await screen.findByText("Acme")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Money in" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Acme/ })).not.toBeInTheDocument();
  });
});
