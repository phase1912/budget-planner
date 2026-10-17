import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DataCard } from "./DataCard";

const stores = vi.hoisted(() => ({
  exportStore: { busy: {}, start: vi.fn() },
  accountStore: {
    state: { status: "idle", error: null as string | null, isLoading: false },
    reset: vi.fn(),
    deleteAccount: vi.fn(),
  },
}));

vi.mock("@/stores/StoreContext", () => ({ useStores: () => stores }));

const renderCard = () =>
  render(
    <MemoryRouter>
      <DataCard />
    </MemoryRouter>,
  );

describe("DataCard (F17.9.1-2)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("downloads everything held about the user as one archive", () => {
    renderCard();

    fireEvent.click(screen.getByRole("button", { name: /Download everything/ }));

    expect(stores.exportStore.start).toHaveBeenCalledWith({
      kind: "account",
      format: "zip",
      compare: false,
    });
    expect(screen.getByRole("link", { name: "Privacy policy" })).toHaveAttribute(
      "href",
      "/privacy",
    );
  });

  it("deletes the account only with the password, after saying what goes", () => {
    renderCard();

    fireEvent.click(screen.getByRole("button", { name: /Delete account/ }));
    const confirm = screen.getByRole("button", { name: "Delete for good" });
    expect(confirm).toBeDisabled();
    expect(screen.getByText(/This cannot be undone/)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Your password"), { target: { value: "secret" } });
    fireEvent.click(confirm);

    expect(stores.accountStore.deleteAccount).toHaveBeenCalledWith("secret");
  });
});
