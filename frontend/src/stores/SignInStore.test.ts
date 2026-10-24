import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { AuthStore } from "./AuthStore";
import { SignInStore } from "./SignInStore";
import type { ToastStore } from "./ToastStore";

describe("SignInStore (F1.6.2)", () => {
  let api: { GET: ReturnType<typeof vi.fn>; POST: ReturnType<typeof vi.fn> };
  let auth: { adoptSession: ReturnType<typeof vi.fn>; secondFactorToken: string | null };
  let store: SignInStore;
  const assign = vi.fn();

  beforeEach(() => {
    sessionStorage.clear();
    assign.mockClear();
    vi.stubGlobal("location", { assign, origin: "https://app.test", pathname: "/", hash: "" });
    api = { GET: vi.fn(), POST: vi.fn() };
    auth = { adoptSession: vi.fn(), secondFactorToken: null };
    store = new SignInStore(
      api as unknown as ApiClient,
      auth as unknown as AuthStore,
      { showSuccess: vi.fn(), showError: vi.fn() } as unknown as ToastStore,
    );
  });

  /** Leave for the provider, and come back with what it would put in the fragment. */
  async function roundTrip(fragment: Record<string, string> = {}) {
    api.GET.mockResolvedValueOnce({ data: { google: "web-client", apple: null } });
    await store.loadProviders();
    store.start("google");
    const sent = new URL(String(assign.mock.calls[0]?.[0]));
    const state = sent.searchParams.get("state") ?? "";
    const query = new URLSearchParams({ state, id_token: "tok", ...fragment });
    return { sent, result: await store.finish("google", `#${query.toString()}`) };
  }

  it("offers only the providers the server has switched on", async () => {
    api.GET.mockResolvedValueOnce({ data: { google: null, apple: "services-id" } });

    await store.loadProviders();

    expect(store.available).toEqual(["apple"]);
  });

  it("goes to the provider with a fresh nonce and signs in with the token it returns", async () => {
    api.POST.mockResolvedValueOnce({
      data: { user: { id: "u1" }, access_token: "a", refresh_token: "r" },
    });

    const { sent, result } = await roundTrip();

    expect(sent.origin).toBe("https://accounts.google.com");
    expect(sent.searchParams.get("redirect_uri")).toBe("https://app.test/auth/callback/google");
    const body = (api.POST.mock.calls[0]?.[1] as { body: { nonce: string } }).body;
    expect(body.nonce).toBe(sent.searchParams.get("nonce"));
    expect(result).toBe("signed-in");
    expect(auth.adoptSession).toHaveBeenCalledWith({ id: "u1" }, "a", "r");
  });

  it("refuses an answer that does not belong to the sign-in it started", async () => {
    api.GET.mockResolvedValueOnce({ data: { google: "web-client", apple: null } });
    await store.loadProviders();
    store.start("google");

    const result = await store.finish("google", "#state=someone-elses&id_token=tok");

    expect(result).toBe("failed");
    expect(api.POST).not.toHaveBeenCalled();
  });

  it("asks for the terms before a new account, then sends them accepted", async () => {
    api.POST.mockResolvedValueOnce({ error: { code: "terms_required", detail: "x" } });
    api.POST.mockResolvedValueOnce({
      data: { user: { id: "u1" }, access_token: "a", refresh_token: "r" },
    });

    const { result } = await roundTrip();
    const again = await store.answer({ accept_terms: true });

    expect(result).toBe("needs-terms");
    expect(again).toBe("signed-in");
    const body = (api.POST.mock.calls[1]?.[1] as { body: { accept_terms: boolean } }).body;
    expect(body.accept_terms).toBe(true);
  });

  it("asks for the password of an account the address already has", async () => {
    api.POST.mockResolvedValueOnce({ error: { code: "link_needs_password", detail: "x" } });

    const { result } = await roundTrip();

    expect(result).toBe("needs-password");
  });

  it("hands a two-factor account on to the code step", async () => {
    api.POST.mockResolvedValueOnce({ data: { second_factor_token: "challenge" } });

    const { result } = await roundTrip();

    expect(result).toBe("second-factor");
    expect(auth.secondFactorToken).toBe("challenge");
  });
});
