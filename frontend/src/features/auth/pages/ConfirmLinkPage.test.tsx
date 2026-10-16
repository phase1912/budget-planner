import { StrictMode } from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ConfirmLinkPage } from "./ConfirmLinkPage";

const account = vi.hoisted(() => ({
  state: { status: "idle", error: null as string | null, isLoading: false },
  confirmedEmail: null as string | null,
  reset: vi.fn(),
  confirmEmail: vi.fn(),
  confirmEmailChange: vi.fn(),
}));

vi.mock("@/stores/StoreContext", () => ({
  useStores: () => ({ accountStore: account, authStore: { isAuthenticated: false } }),
}));

const open = (path: string, kind: "address" | "change") =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="*" element={<ConfirmLinkPage kind={kind} />} />
      </Routes>
    </MemoryRouter>,
  );

describe("ConfirmLinkPage (F17.8.2)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    account.state = { status: "idle", error: null, isLoading: false };
  });

  it("follows the link from the letter once, even when effects run twice", () => {
    render(
      <StrictMode>
        <MemoryRouter initialEntries={["/confirm-email?token=abc"]}>
          <ConfirmLinkPage kind="address" />
        </MemoryRouter>
      </StrictMode>,
    );

    expect(account.confirmEmail).toHaveBeenCalledWith("abc");
    expect(account.confirmEmail).toHaveBeenCalledTimes(1);
    expect(account.confirmEmailChange).not.toHaveBeenCalled();
  });

  it("says the address is confirmed and offers to sign in", () => {
    account.state = { status: "success", error: null, isLoading: false };
    open("/confirm-email?token=abc", "address");

    expect(
      screen.getByText("Your address is confirmed. You can now add receipts."),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/login");
  });

  it("explains a page opened without a link", () => {
    open("/confirm-email-change", "change");

    expect(screen.getByText("This page opens from the link in the letter.")).toBeInTheDocument();
    expect(account.confirmEmailChange).not.toHaveBeenCalled();
  });
});
