import { beforeEach, describe, expect, it, vi } from "vitest";

import { ExplorationStore } from "./ExplorationStore";
import type { ToastStore } from "./ToastStore";

const api = vi.hoisted(() => ({ GET: vi.fn(), POST: vi.fn(), DELETE: vi.fn() }));
vi.mock("@/api/client", () => ({ apiClient: api }));

const EMPTY = { totals: { times: 0, spent: "0", quantities: {} }, months: [], products: [] };

describe("ExplorationStore (F16.2)", () => {
  let toast: { showSuccess: ReturnType<typeof vi.fn>; showError: ReturnType<typeof vi.fn> };
  let store: ExplorationStore;

  beforeEach(() => {
    vi.clearAllMocks();
    toast = { showSuccess: vi.fn(), showError: vi.fn() };
    store = new ExplorationStore(toast as unknown as ToastStore);
  });

  it("asks for all time without dates, and for a period with both", async () => {
    api.GET.mockResolvedValue({ data: EMPTY });
    store.setProducts(["p1"]);
    store.choosePreset("all");
    await vi.waitFor(() => {
      expect(api.GET).toHaveBeenLastCalledWith("/api/v1/products/explore", {
        params: { query: { product_ids: ["p1"] } },
      });
    });

    store.chooseRange("2026-09-01", "2026-09-30");

    await vi.waitFor(() => {
      expect(api.GET).toHaveBeenLastCalledWith("/api/v1/products/explore", {
        params: { query: { product_ids: ["p1"], start: "2026-09-01", end: "2026-09-30" } },
      });
    });
  });

  it("nothing ticked is nothing to explore", () => {
    store.setProducts([]);

    expect(store.result).toBeNull();
    expect(api.GET).not.toHaveBeenCalled();
  });

  it("saves the ticked products under a name and lists it", async () => {
    api.GET.mockResolvedValue({ data: EMPTY });
    store.setProducts(["p1", "p2"]);
    api.POST.mockResolvedValueOnce({
      data: { id: "s1", name: "Snacks", product_ids: ["p1", "p2"] },
    });

    expect(await store.saveSelection("Snacks")).toBe(true);

    expect(api.POST).toHaveBeenCalledWith("/api/v1/products/selections", {
      body: { name: "Snacks", product_ids: ["p1", "p2"] },
    });
    expect(store.selections.map((s) => s.name)).toEqual(["Snacks"]);
  });
});
