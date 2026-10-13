import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/api/client";
import i18n from "@/i18n";
import type { AuthStore } from "@/stores/AuthStore";
import { LanguageStore } from "./LanguageStore";

vi.mock("@/api/client", () => ({ apiClient: { PATCH: vi.fn() } }));

const patch = vi.mocked(apiClient.PATCH);

function signedIn(language: string | null): AuthStore {
  return {
    user: {
      id: "u1",
      email: "a@x",
      first_name: "A",
      last_name: "B",
      currency: "PLN",
      language,
      forwarding_address: "",
    },
  } as unknown as AuthStore;
}

describe("LanguageStore (F9.9)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });
  afterEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("shows a chosen language at once and remembers it on this browser", async () => {
    const store = new LanguageStore({ user: null } as unknown as AuthStore);

    await store.choose("pl");

    expect(i18n.language).toBe("pl");
    expect(localStorage.getItem("budget_language")).toBe("pl");
    expect(document.documentElement.lang).toBe("pl");
    expect(patch).not.toHaveBeenCalled();
  });

  it("keeps a signed-in user's choice with their account", async () => {
    patch.mockResolvedValue({ data: {} } as never);
    const auth = signedIn("en");
    const store = new LanguageStore(auth);

    await store.choose("uk");

    expect(patch).toHaveBeenCalledWith("/users/me", { body: { language: "uk" } });
    expect(auth.user?.language).toBe("uk");
  });

  it("takes the account's language when the user signs in", () => {
    const store = new LanguageStore(signedIn("pl"));

    store.adoptAccount("pl");

    expect(store.language).toBe("pl");
    expect(patch).not.toHaveBeenCalled();
  });

  it("gives an account that never chose one the language already in use", () => {
    patch.mockResolvedValue({ data: {} } as never);
    const store = new LanguageStore(signedIn(null));
    store.language = "uk";

    store.adoptAccount(null);

    expect(patch).toHaveBeenCalledWith("/users/me", { body: { language: "uk" } });
  });
});
