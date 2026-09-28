import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/api/client";
import { GoalsStore } from "./GoalsStore";
import type { Goal } from "./GoalsStore";
import type { ToastStore } from "./ToastStore";

vi.mock("@/api/client", () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() },
}));

function goal(id: string, name: string): Goal {
  return {
    id,
    type: "financial",
    financial_kind: "spending_ceiling",
    name,
    description: null,
    target_amount: "3000.00",
    category_id: null,
    mapped_category_ids: [],
    mapped_item_names: [],
    created_at: "2026-09-28T10:00:00Z",
    updated_at: "2026-09-28T10:00:00Z",
  };
}

// The client's response types differ per route; the store reads only data and error.
const ok = (data: unknown) => ({ data, response: new Response() }) as never;
const refused = (detail: string) =>
  ({
    error: { title: "Unprocessable", status: 422, detail },
    response: new Response(),
  }) as never;

describe("GoalsStore", () => {
  let toast: { showSuccess: ReturnType<typeof vi.fn> };
  let store: GoalsStore;

  beforeEach(() => {
    vi.mocked(apiClient.GET).mockReset();
    vi.mocked(apiClient.POST).mockReset();
    vi.mocked(apiClient.PATCH).mockReset();
    vi.mocked(apiClient.DELETE).mockReset();
    toast = { showSuccess: vi.fn() };
    store = new GoalsStore(toast as unknown as ToastStore);
  });

  it("loads the user's goals", async () => {
    vi.mocked(apiClient.GET).mockResolvedValue(ok([goal("1", "Ceiling")]));
    await store.load();
    expect(store.goals.map((g) => g.name)).toEqual(["Ceiling"]);
    expect(store.isLoading).toBe(false);
  });

  it("keeps the reason a load failed", async () => {
    vi.mocked(apiClient.GET).mockResolvedValue(refused("Token expired."));
    await store.load();
    expect(store.loadError).toBe("Token expired.");
  });

  it("puts a new goal first and says it was added", async () => {
    store.goals = [goal("1", "Older")];
    vi.mocked(apiClient.POST).mockResolvedValue(ok(goal("2", "Newer")));
    const saved = await store.create({ type: "financial", name: "Newer" });
    expect(saved).toBe(true);
    expect(store.goals.map((g) => g.name)).toEqual(["Newer", "Older"]);
    expect(toast.showSuccess).toHaveBeenCalledWith("Goal added");
  });

  it("keeps the server's reason when it refuses a goal, and leaves the list alone", async () => {
    store.goals = [goal("1", "Older")];
    vi.mocked(apiClient.POST).mockResolvedValue(refused("Pick the category to cut."));
    const saved = await store.create({ type: "financial", name: "Cut" });
    expect(saved).toBe(false);
    expect(store.saveError).toBe("Pick the category to cut.");
    expect(store.goals).toHaveLength(1);
    expect(toast.showSuccess).not.toHaveBeenCalled();
  });

  it("replaces an edited goal in place", async () => {
    store.goals = [goal("1", "First"), goal("2", "Second")];
    vi.mocked(apiClient.PATCH).mockResolvedValue(ok(goal("2", "Renamed")));
    await store.update("2", { name: "Renamed" });
    expect(store.goals.map((g) => g.name)).toEqual(["First", "Renamed"]);
  });

  it("drops a removed goal", async () => {
    store.goals = [goal("1", "First"), goal("2", "Second")];
    vi.mocked(apiClient.DELETE).mockResolvedValue({ response: new Response() } as never);
    expect(await store.remove("1")).toBe(true);
    expect(store.goals.map((g) => g.id)).toEqual(["2"]);
    expect(toast.showSuccess).toHaveBeenCalledWith("Goal removed");
  });

  it("forgets everything for the next user", () => {
    store.goals = [goal("1", "First")];
    store.saveError = "x";
    store.reset();
    expect(store.goals).toEqual([]);
    expect(store.saveError).toBeNull();
  });
});
