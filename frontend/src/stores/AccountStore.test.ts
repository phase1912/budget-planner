import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { AccountStore } from "./AccountStore";
import type { AuthStore, User } from "./AuthStore";
import type { ToastStore } from "./ToastStore";

const USER = { id: "u1", email: "ann@example.com", email_confirmed: false } as User;

describe("AccountStore (F17.8)", () => {
  let api: { POST: ReturnType<typeof vi.fn> };
  let auth: { user: User | null; logoutLocally: ReturnType<typeof vi.fn> };
  let store: AccountStore;

  beforeEach(() => {
    api = { POST: vi.fn() };
    auth = { user: { ...USER }, logoutLocally: vi.fn() };
    const toast = { showSuccess: vi.fn(), showError: vi.fn() };
    store = new AccountStore(
      api as unknown as ApiClient,
      auth as unknown as AuthStore,
      toast as unknown as ToastStore,
    );
  });

  it("asks to confirm only an account the server says is unconfirmed", () => {
    expect(store.mustConfirm).toBe(true);
    // A session kept from before confirmation existed has no flag: the account was confirmed.
    auth.user = { id: "u1", email: "old@example.com" } as User;
    expect(store.mustConfirm).toBe(false);
  });

  it("marks the signed-in user confirmed once the link is followed", async () => {
    api.POST.mockResolvedValueOnce({ data: { ...USER, email_confirmed: true } });

    await store.confirmEmail("tok");

    expect(api.POST).toHaveBeenCalledWith("/auth/confirm-email", { body: { token: "tok" } });
    expect(store.mustConfirm).toBe(false);
    expect(store.state.status).toBe("success");
  });

  it("says why a link was refused", async () => {
    api.POST.mockResolvedValueOnce({ error: { code: "link_invalid", detail: "Expired." } });

    await store.confirmEmail("old");

    expect(store.state.error).toBe("Expired.");
    expect(store.mustConfirm).toBe(true);
  });

  it("signs out here too once a reset ended every session", async () => {
    api.POST.mockResolvedValueOnce({ data: { message: "ok" } });

    await store.resetPassword("tok", "New-Secret-42");

    expect(auth.logoutLocally).toHaveBeenCalled();
  });

  it("asks for the reset letter in the language of the screen", async () => {
    api.POST.mockResolvedValueOnce({ data: { message: "ok" } });

    await store.forgotPassword("ann@example.com");

    expect(api.POST).toHaveBeenCalledWith("/auth/password/forgot", {
      body: { email: "ann@example.com", language: "en" },
    });
  });
});
