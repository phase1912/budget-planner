import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { AuthStore, User } from "./AuthStore";
import type { ToastStore } from "./ToastStore";
import { TwoFactorStore } from "./TwoFactorStore";

const USER = { id: "u1", email: "ann@example.com", two_factor_enabled: false } as User;

describe("TwoFactorStore (F18.6.1)", () => {
  let api: { POST: ReturnType<typeof vi.fn> };
  let auth: {
    user: User | null;
    adoptSession: ReturnType<typeof vi.fn>;
    updateUser: ReturnType<typeof vi.fn>;
  };
  let store: TwoFactorStore;

  beforeEach(() => {
    api = { POST: vi.fn() };
    auth = { user: { ...USER }, adoptSession: vi.fn(), updateUser: vi.fn() };
    store = new TwoFactorStore(
      api as unknown as ApiClient,
      auth as unknown as AuthStore,
      { showSuccess: vi.fn() } as unknown as ToastStore,
    );
  });

  it("turns it on with a code, shows the recovery codes once and takes the stronger session", async () => {
    api.POST.mockResolvedValueOnce({ data: { secret: "S", uri: "otpauth://x", qr_svg: "<svg/>" } });
    await store.begin();
    expect(store.setup?.secret).toBe("S");

    api.POST.mockResolvedValueOnce({
      data: { recovery_codes: ["a", "b"], access_token: "A2", refresh_token: "R2" },
    });
    expect(await store.confirm(" 123456 ")).toBe(true);

    expect(api.POST).toHaveBeenLastCalledWith("/users/me/two-factor/confirm", {
      body: { code: "123456" },
    });
    expect(auth.adoptSession).toHaveBeenCalledWith(
      { ...USER, two_factor_enabled: true },
      "A2",
      "R2",
    );
    expect(store.setup).toBeNull();
    expect(store.recoveryCodes).toEqual(["a", "b"]);
    store.close();
    expect(store.recoveryCodes).toBeNull();
  });

  it("keeps the setup open on a wrong code", async () => {
    api.POST.mockResolvedValueOnce({ data: { secret: "S", uri: "u", qr_svg: "<svg/>" } });
    await store.begin();
    api.POST.mockResolvedValueOnce({ error: { detail: "The code is not right." } });

    expect(await store.confirm("000000")).toBe(false);
    expect(store.setup).not.toBeNull();
    expect(store.state.error).toBe("The code is not right.");
  });

  it("turns it off with the password and a code", async () => {
    auth.user = { ...USER, two_factor_enabled: true };
    api.POST.mockResolvedValueOnce({ data: undefined });

    expect(await store.disable("pw", "123456")).toBe(true);
    expect(auth.updateUser).toHaveBeenCalledWith({ ...USER, two_factor_enabled: false });
  });
});
