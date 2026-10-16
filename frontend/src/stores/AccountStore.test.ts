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

describe("AccountStore account deletion (F17.9.1)", () => {
  it("signs out here once the account is deleted, and keeps it on a wrong password", async () => {
    const api = { DELETE: vi.fn() };
    const auth = { user: { ...USER }, logoutLocally: vi.fn() };
    const toast = { showSuccess: vi.fn(), showError: vi.fn() };
    const store = new AccountStore(
      api as unknown as ApiClient,
      auth as unknown as AuthStore,
      toast as unknown as ToastStore,
    );

    api.DELETE.mockResolvedValueOnce({ error: { code: "invalid_credentials", detail: "No." } });
    expect(await store.deleteAccount("wrong")).toBe(false);
    expect(auth.logoutLocally).not.toHaveBeenCalled();

    api.DELETE.mockResolvedValueOnce({ data: undefined, response: new Response(null) });
    expect(await store.deleteAccount("right")).toBe(true);
    expect(api.DELETE).toHaveBeenLastCalledWith("/users/me", { body: { password: "right" } });
    expect(auth.logoutLocally).toHaveBeenCalled();
  });
});
