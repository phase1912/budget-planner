import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { AdminStore } from "./AdminStore";
import type { ToastStore } from "./ToastStore";

describe("AdminStore (F18.6)", () => {
  let api: Record<"GET" | "POST" | "PUT", ReturnType<typeof vi.fn>>;
  let toast: { showSuccess: ReturnType<typeof vi.fn> };
  let store: AdminStore;

  beforeEach(() => {
    api = { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn() };
    toast = { showSuccess: vi.fn() };
    store = new AdminStore(api as unknown as ApiClient, toast as unknown as ToastStore);
  });

  it("sends an admin signed in with the password alone to two-factor sign-in", async () => {
    api.GET.mockResolvedValueOnce({ error: { code: "second_factor_required" } });
    await store.checkAccess();
    expect(store.access).toBe("second_factor");

    api.GET.mockResolvedValueOnce({ data: { items: [], total: 0 } });
    await store.checkAccess();
    expect(store.access).toBe("open");
  });

  it("searches from the first page with the chosen filter", async () => {
    api.GET.mockResolvedValue({ data: { items: [], total: 0 } });
    store.page = 3;
    store.filter = "unconfirmed";

    store.search(" ann ");
    await vi.waitFor(() => {
      expect(api.GET).toHaveBeenCalled();
    });

    expect(api.GET).toHaveBeenCalledWith("/api/v1/admin/users", {
      params: { query: { q: "ann", limit: 25, offset: 0, confirmed: false } },
    });
  });

  it("grants a plan, says so and reloads the card", async () => {
    api.POST.mockResolvedValueOnce({ data: { id: "g1" } });
    api.GET.mockResolvedValueOnce({ data: { id: "u1", grants: [{ id: "g1" }] } });

    const done = await store.grantPlan("u1", 30, "  Beta tester ");

    expect(done).toBe(true);
    expect(api.POST).toHaveBeenCalledWith("/api/v1/admin/users/{user_id}/grants", {
      params: { path: { user_id: "u1" } },
      body: { days: 30, reason: "Beta tester" },
    });
    expect(toast.showSuccess).toHaveBeenCalledWith("The plan is granted.");
    expect(store.card?.id).toBe("u1");
  });

  it("keeps a refused action's reason on screen and does not reload", async () => {
    api.PUT.mockResolvedValueOnce({ error: { detail: "Only a super admin can do this." } });

    const done = await store.setAdmin("u1", true);

    expect(done).toBe(false);
    expect(store.actionState.error).toBe("Only a super admin can do this.");
    expect(api.GET).not.toHaveBeenCalled();
  });
});
