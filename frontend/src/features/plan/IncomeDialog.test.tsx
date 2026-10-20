import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/api/client";
import type { BankAccount } from "@/stores/BankAccountsStore";
import { RootStore } from "@/stores/RootStore";
import { StoreProvider } from "@/stores/StoreContext";
import { IncomeDialog } from "./IncomeDialog";

vi.mock("@/api/client", () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), use: vi.fn() },
}));

type Call = (path: string, options?: { body?: unknown }) => Promise<unknown>;
const api = apiClient as unknown as Record<"GET" | "POST", ReturnType<typeof vi.fn<Call>>>;

const account = (fields: Partial<BankAccount>): BankAccount => ({
  id: "card",
  name: "Our card",
  kind: "personal",
  opening: "0",
  opening_on: "2026-10-01",
  tax_rate: null,
  for_purchases: true,
  balance: "0",
  set_aside: "0",
  shared: false,
  mine: true,
  added_by: null,
  ...fields,
});

describe("adding income onto an account (F23.15)", () => {
  let store: RootStore;

  beforeEach(() => {
    vi.clearAllMocks();
    store = new RootStore();
    store.authStore.user = { id: "me", currency: "PLN" } as typeof store.authStore.user;
    const accounts = [
      account({ id: "biz", name: "Business", kind: "business", for_purchases: false }),
      account({}),
    ];
    store.bankAccountsStore.accounts = accounts;
    api.GET.mockImplementation((path: string) =>
      Promise.resolve({
        data: path === "/api/v1/accounts" ? { accounts, total: "0", set_aside: "0" } : [],
      }),
    );
    api.POST.mockResolvedValue({ data: {} });
  });

  const open = () =>
    render(
      <StoreProvider store={store}>
        <IncomeDialog entry={null} defaultDay="2026-10-20" onClose={vi.fn()} onSaved={vi.fn()} />
      </StoreProvider>,
    );

  it("lands on the purchase card unless another account is picked", async () => {
    open();

    expect(screen.getByLabelText("To which account")).toHaveValue("card");
    fireEvent.change(screen.getByLabelText("Amount"), { target: { value: "500" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(api.POST).toHaveBeenCalledWith("/api/v1/income", {
        body: expect.objectContaining({ amount: "500", account_id: "card" }) as unknown,
      });
    });
  });

  it("comes every month as a regular income on that account", async () => {
    open();

    fireEvent.click(screen.getByRole("switch", { name: "Every month" }));
    fireEvent.change(screen.getByLabelText("Amount"), { target: { value: "9000" } });
    fireEvent.change(screen.getByLabelText("Comes on"), { target: { value: "10" } });
    fireEvent.click(screen.getByRole("radio", { name: "About, it varies" }));
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(api.POST).toHaveBeenCalledWith(
        "/api/v1/income/regular",
        expect.objectContaining({
          body: expect.objectContaining({
            amount: "9000",
            day: 10,
            about: true,
            account_id: "card",
          }) as unknown,
        }),
      );
    });
  });

  it("from another own account is a transfer, never income", async () => {
    open();

    fireEvent.click(screen.getByRole("radio", { name: "From our other account" }));
    fireEvent.change(screen.getByLabelText("From account"), { target: { value: "biz" } });
    fireEvent.change(screen.getByLabelText("Amount"), { target: { value: "6000" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(api.POST).toHaveBeenCalledWith(
        "/api/v1/accounts/moves",
        expect.objectContaining({
          body: expect.objectContaining({
            from_account_id: "biz",
            to_account_id: "card",
            amount: "6000",
          }) as unknown,
        }),
      );
    });
    expect(api.POST).not.toHaveBeenCalledWith("/api/v1/income", expect.anything());
  });
});
