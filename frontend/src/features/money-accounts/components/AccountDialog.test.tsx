import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { BankAccount } from "@/stores/BankAccountsStore";
import { AccountDialog } from "./AccountDialog";

const CARD = {
  id: "a1",
  name: "My card",
  kind: "personal",
  opening: "0",
  opening_on: "2026-10-01",
  tax_rate: null,
  for_purchases: true,
  balance: "100.00",
  set_aside: "0",
  shared: false,
  mine: true,
  added_by: null,
} as BankAccount;

const stores = vi.hoisted(() => ({
  bankAccountsStore: {
    accounts: [] as unknown[],
    saveState: { isLoading: false },
    remove: vi.fn().mockResolvedValue(true),
  },
  householdStore: { mayShare: false },
  authStore: { user: { currency: "PLN" } },
}));

vi.mock("@/stores/StoreContext", () => ({ useStores: () => stores }));

describe("AccountDialog (F23.15, F23.21)", () => {
  it("says the last card's removal stops the balance and regular incomes, not the budget", () => {
    stores.bankAccountsStore.accounts = [CARD];
    render(<AccountDialog account={CARD} today="2026-10-20" onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Delete account" }));

    expect(screen.getByRole("alert")).toHaveTextContent(/your last card/);
    expect(stores.bankAccountsStore.remove).not.toHaveBeenCalled();
  });

  it("asks the usual question while another card stays", () => {
    stores.bankAccountsStore.accounts = [CARD, { ...CARD, id: "a2" }];
    render(<AccountDialog account={CARD} today="2026-10-20" onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Delete account" }));

    expect(screen.getByRole("alert")).not.toHaveTextContent(/your last card/);
  });
});
