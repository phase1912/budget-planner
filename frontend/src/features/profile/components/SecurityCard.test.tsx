import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SecurityCard } from "./SecurityCard";

const stores = vi.hoisted(() => ({
  authStore: { user: { is_admin: false } },
  twoFactorStore: {
    enabled: false,
    setup: null as null | { secret: string; uri: string; qr_svg: string },
    recoveryCodes: null as string[] | null,
    state: { isLoading: false, error: null as string | null },
    begin: vi.fn(),
    confirm: vi.fn(),
    disable: vi.fn().mockResolvedValue(true),
    close: vi.fn(),
  },
}));

vi.mock("@/stores/StoreContext", () => ({ useStores: () => stores }));

const renderCard = () =>
  render(
    <MemoryRouter>
      <SecurityCard />
    </MemoryRouter>,
  );

describe("SecurityCard (F18.6.1)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.assign(stores.twoFactorStore, { enabled: false, setup: null, recoveryCodes: null });
    stores.authStore.user = { is_admin: false };
  });

  it("offers to turn it on, and tells an admin they need it", () => {
    renderCard();
    expect(screen.queryByText(/you need it/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Turn on" }));
    expect(stores.twoFactorStore.begin).toHaveBeenCalled();

    stores.authStore.user = { is_admin: true };
    renderCard();
    expect(screen.getByText(/you need it to open the admin pages/)).toBeInTheDocument();
  });

  it("shows the QR code and the key, and confirms with a code from the app", () => {
    stores.twoFactorStore.setup = { secret: "ABCD", uri: "otpauth://x", qr_svg: "<svg/>" };
    renderCard();

    expect(screen.getByRole("img", { name: /QR code/ })).toBeInTheDocument();
    expect(screen.getByText("ABCD")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Code from the app"), { target: { value: "123456" } });
    const dialog = screen.getByRole("dialog");
    const form = dialog.querySelector("form");
    expect(form).not.toBeNull();
    if (form) fireEvent.submit(form);
    expect(stores.twoFactorStore.confirm).toHaveBeenCalledWith("123456");
  });

  it("shows the recovery codes once they are issued", () => {
    stores.twoFactorStore.recoveryCodes = ["aaaa-bbbb", "cccc-dddd"];
    renderCard();

    expect(screen.getByText("aaaa-bbbb")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "I saved them" }));
    expect(stores.twoFactorStore.close).toHaveBeenCalled();
  });
});
