import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { AuthStore, type User } from "./AuthStore";

const USER = { id: "u1", email: "ann@example.com" } as User;

describe("AuthStore two-factor sign-in (F18.6.1)", () => {
  let api: { POST: ReturnType<typeof vi.fn>; use: ReturnType<typeof vi.fn> };
  let store: AuthStore;

  beforeEach(() => {
    localStorage.clear();
    api = { POST: vi.fn(), use: vi.fn() };
    store = new AuthStore(api as unknown as ApiClient);
  });

  it("holds the challenge after the password and signs in only with the code", async () => {
    api.POST.mockResolvedValueOnce({
      data: { second_factor_required: true, second_factor_token: "challenge" },
    });

    expect(await store.login({ email: USER.email, password: "pw" })).toBe(false);
    expect(store.secondFactorToken).toBe("challenge");
    expect(store.isAuthenticated).toBe(false);

    api.POST.mockResolvedValueOnce({
      data: { user: USER, access_token: "A", refresh_token: "R" },
    });
    expect(await store.completeSecondFactor(" 123456 ")).toBe(true);

    expect(api.POST).toHaveBeenLastCalledWith("/auth/login/second-factor", {
      body: { token: "challenge", code: "123456" },
    });
    expect(store.secondFactorToken).toBeNull();
    expect(store.isAuthenticated).toBe(true);
  });

  it("keeps the code step open after a wrong code, and can go back", async () => {
    store.secondFactorToken = "challenge";
    api.POST.mockResolvedValueOnce({ error: { detail: "The code is not right." } });

    expect(await store.completeSecondFactor("000000")).toBe(false);
    expect(store.authState.error).toBe("The code is not right.");
    expect(store.secondFactorToken).toBe("challenge");

    store.cancelSecondFactor();
    expect(store.secondFactorToken).toBeNull();
  });
});
