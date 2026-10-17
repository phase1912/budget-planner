import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AdminLayout } from "./AdminLayout";

const stores = vi.hoisted(() => ({
  authStore: {
    user: null as null | {
      is_admin: boolean;
      is_super_admin: boolean;
      two_factor_enabled: boolean;
    },
    logout: vi.fn(),
  },
  adminStore: { access: "open", checkAccess: vi.fn() },
}));

vi.mock("@/stores/StoreContext", () => ({ useStores: () => stores }));

const renderAt = () =>
  render(
    <MemoryRouter initialEntries={["/admin"]}>
      <Routes>
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<p>inside</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );

describe("AdminLayout (F18.6)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    stores.authStore.user = { is_admin: true, is_super_admin: false, two_factor_enabled: true };
    stores.adminStore.access = "open";
  });

  it("is a page that does not exist for anyone but an admin", () => {
    stores.authStore.user = { is_admin: false, is_super_admin: false, two_factor_enabled: false };
    renderAt();

    expect(screen.queryByText("inside")).not.toBeInTheDocument();
    expect(stores.adminStore.checkAccess).not.toHaveBeenCalled();
  });

  it("shows the log tab to super admins only", () => {
    renderAt();
    expect(screen.getByText("inside")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Log" })).not.toBeInTheDocument();

    stores.authStore.user = { is_admin: true, is_super_admin: true, two_factor_enabled: true };
    renderAt();
    expect(screen.getByRole("link", { name: "Log" })).toBeInTheDocument();
  });

  it("sends an admin without two-factor sign-in to set it up instead of opening", () => {
    stores.authStore.user = { is_admin: true, is_super_admin: false, two_factor_enabled: false };
    stores.adminStore.access = "second_factor";
    renderAt();

    expect(screen.queryByText("inside")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Set it up" })).toHaveAttribute(
      "href",
      "/profile#security",
    );
  });
});
