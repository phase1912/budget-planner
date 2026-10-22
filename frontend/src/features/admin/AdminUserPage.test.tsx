import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AdminUserCard } from "@/stores/AdminStore";
import { AdminUserPage } from "./AdminUserPage";

const CARD: AdminUserCard = {
  id: "u1",
  email: "ann@example.com",
  first_name: "Ann",
  last_name: "Lee",
  created_at: "2026-09-01T10:00:00Z",
  email_confirmed_at: null,
  onboarded_at: "2026-09-01T10:05:00Z",
  language: "uk",
  terms_version: "2026-10",
  is_admin: false,
  is_super_admin: false,
  two_factor_enabled: false,
  plan: "paid",
  plan_ends_on: "2026-11-16",
  credits_limit: 2500,
  credits_used: 12,
  last_active_at: null,
  grants: [
    {
      id: "g1",
      plan: "paid",
      starts_at: "2026-10-17T00:00:00Z",
      ends_at: "2026-11-16T00:00:00Z",
      reason: "Beta tester",
      granted_by: "boss@example.com",
      revoked_at: null,
      created_at: "2026-10-17T00:00:00Z",
    },
  ],
  activity: [{ event: "signed_in", created_at: "2026-10-17T09:00:00Z" }],
};

const stores = vi.hoisted(() => ({
  authStore: { user: { id: "me", is_super_admin: false }, updateUser: vi.fn() },
  adminStore: {
    card: null as AdminUserCard | null,
    cardState: { error: null as string | null },
    actionState: { isLoading: false, error: null as string | null },
    loadCard: vi.fn(),
    confirmEmail: vi.fn(),
    sendConfirmation: vi.fn(),
    sendPasswordReset: vi.fn(),
    restartOnboarding: vi.fn().mockResolvedValue(true),
    grantPlan: vi.fn().mockResolvedValue(true),
    revokeGrant: vi.fn(),
    setAdmin: vi.fn(),
  },
}));

vi.mock("@/stores/StoreContext", () => ({ useStores: () => stores }));

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={["/admin/users/u1"]}>
      <Routes>
        <Route path="/admin/users/:id" element={<AdminUserPage />} />
      </Routes>
    </MemoryRouter>,
  );

describe("AdminUserPage (F18.6.2-3)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    stores.adminStore.card = CARD;
    stores.authStore.user = { id: "me", is_super_admin: false };
  });

  it("shows the account, its plan, grants and activity, and offers the support actions", () => {
    renderPage();

    expect(stores.adminStore.loadCard).toHaveBeenCalledWith("u1");
    expect(screen.getByRole("heading", { name: "ann@example.com" })).toBeInTheDocument();
    expect(screen.getByText("12 of 2500")).toBeInTheDocument();
    expect(screen.getByText(/Beta tester/)).toBeInTheDocument();
    expect(screen.getByText("Signed in")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Confirm address" }));
    expect(stores.adminStore.confirmEmail).toHaveBeenCalledWith("u1");
    fireEvent.click(screen.getByRole("button", { name: "Send password reset link" }));
    expect(stores.adminStore.sendPasswordReset).toHaveBeenCalledWith("u1");
  });

  it("grants the paid plan for the chosen days with a reason", () => {
    renderPage();

    fireEvent.change(screen.getByLabelText("For"), { target: { value: "90" } });
    fireEvent.change(screen.getByLabelText("Reason"), { target: { value: "Support case" } });
    fireEvent.click(screen.getByRole("button", { name: "Grant" }));

    expect(stores.adminStore.grantPlan).toHaveBeenCalledWith("u1", 90, "Support case");
  });

  it("takes a grant back only after asking", () => {
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Take back" }));
    expect(stores.adminStore.revokeGrant).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Yes" }));
    expect(stores.adminStore.revokeGrant).toHaveBeenCalledWith("u1", "g1");
  });

  it("lets only a super admin appoint an admin", () => {
    renderPage();
    expect(screen.queryByRole("button", { name: "Make admin" })).not.toBeInTheDocument();

    stores.authStore.user = { id: "me", is_super_admin: true };
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Make admin" }));
    fireEvent.click(screen.getByRole("button", { name: "Yes" }));
    expect(stores.adminStore.setAdmin).toHaveBeenCalledWith("u1", true);
  });

  it("shows the setup again, and on one's own account opens it at once", async () => {
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Show the setup again" }));
    await Promise.resolve();
    expect(stores.adminStore.restartOnboarding).toHaveBeenCalledWith("u1");
    expect(stores.authStore.updateUser).not.toHaveBeenCalled();

    stores.authStore.user = { id: "u1", is_super_admin: false };
    fireEvent.click(screen.getByRole("button", { name: "Show the setup again" }));
    await vi.waitFor(() => {
      expect(stores.authStore.updateUser).toHaveBeenCalledWith(
        expect.objectContaining({ id: "u1", onboarded_at: null }),
      );
    });
  });
});
