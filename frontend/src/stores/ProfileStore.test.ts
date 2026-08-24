import { describe, it, expect, vi, beforeEach } from "vitest";
import { ProfileStore } from "./ProfileStore";
import { AuthStore } from "./AuthStore";
import { ToastStore } from "./ToastStore";
import type { ApiClient } from "@/api/client";

describe("ProfileStore", () => {
  let mockApi: unknown;
  let authStore: AuthStore;
  let toastStore: ToastStore;
  let store: ProfileStore;

  beforeEach(() => {
    mockApi = {
      PATCH: vi.fn(),
      use: vi.fn(),
    };
    // stub AuthStore
    authStore = new AuthStore(mockApi as ApiClient);
    authStore.user = {
      id: "uuid",
      email: "test@example.com",
      first_name: "Test",
      last_name: "User",
      currency: "USD",
      budget_limit: null,
    };

    toastStore = new ToastStore();
    store = new ProfileStore(mockApi as ApiClient, authStore, toastStore);
  });

  it("updates profile successfully and syncs authStore", async () => {
    const mockPatch = mockApi as { PATCH: ReturnType<typeof vi.fn> };
    mockPatch.PATCH.mockResolvedValue({
      data: { currency: "EUR", budget_limit: 500 },
      error: undefined,
    });

    const success = await store.updateProfile({ currency: "EUR", budget_limit: 500 });

    expect(success).toBe(true);
    expect(store.updateState.status).toBe("success");
    expect(toastStore.toast?.type).toBe("success");
    expect(authStore.user?.currency).toBe("EUR");
    expect(authStore.user?.budget_limit).toBe(500);
  });

  it("handles api errors gracefully", async () => {
    const mockPatch = mockApi as { PATCH: ReturnType<typeof vi.fn> };
    mockPatch.PATCH.mockResolvedValue({
      data: undefined,
      error: { detail: "Cannot change currency" },
    });

    const success = await store.updateProfile({ currency: "EUR", budget_limit: 500 });

    expect(success).toBe(false);
    expect(store.updateState.status).toBe("error");
    expect(store.updateState.error).toBe("Cannot change currency");
    expect(toastStore.toast?.type).toBe("error");
    expect(authStore.user?.currency).toBe("USD"); // unchanged
  });
});
