import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProductsStore, type Product } from "./ProductsStore";
import type { ToastStore } from "./ToastStore";

const api = vi.hoisted(() => ({ GET: vi.fn(), POST: vi.fn() }));
vi.mock("@/api/client", () => ({ apiClient: api }));

const product = (id: string): Product => ({
  id,
  name: id,
  size_amount: null,
  size_unit: null,
  purchases: 1,
  shops: 1,
  last_bought: null,
  spent: "1.00",
  variants: [],
});

describe("ProductsStore (F16.1)", () => {
  let toast: { showSuccess: ReturnType<typeof vi.fn>; showError: ReturnType<typeof vi.fn> };
  let store: ProductsStore;

  beforeEach(() => {
    vi.clearAllMocks();
    toast = { showSuccess: vi.fn(), showError: vi.fn() };
    store = new ProductsStore(toast as unknown as ToastStore);
  });

  it("keeps the answer to the latest search, not a slower earlier one", async () => {
    let answerFirst: (value: unknown) => void = () => undefined;
    api.GET.mockReturnValueOnce(new Promise((resolve) => (answerFirst = resolve)));
    api.GET.mockResolvedValueOnce({ data: [product("milk")] });

    const first = store.load();
    store.setSearch("milk");
    await vi.waitFor(() => {
      expect(store.products.map((p) => p.id)).toEqual(["milk"]);
    });
    answerFirst({ data: [product("everything")] });
    await first;

    expect(store.products.map((p) => p.id)).toEqual(["milk"]);
  });

  it("merges the other ticked products into the one kept, and clears the ticks", async () => {
    store.toggle("a");
    store.toggle("b");
    api.POST.mockResolvedValueOnce({ data: [product("a")] });

    expect(await store.merge("a")).toBe(true);

    expect(api.POST).toHaveBeenCalledWith("/api/v1/products/{product_id}/merge", {
      params: { path: { product_id: "a" } },
      body: { product_ids: ["b"] },
    });
    expect(store.products.map((p) => p.id)).toEqual(["a"]);
    expect(store.selected).toEqual([]);
    expect(toast.showSuccess).toHaveBeenCalled();
  });

  it("says why a split was refused and keeps the list as it was", async () => {
    store.products = [product("a")];
    api.POST.mockResolvedValueOnce({ error: { detail: "No." } });

    expect(await store.split("a", "alias")).toBe(false);

    expect(toast.showError).toHaveBeenCalledWith("No.");
    expect(store.products.map((p) => p.id)).toEqual(["a"]);
  });
});
