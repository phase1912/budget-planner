import { makeAutoObservable, runInAction } from "mobx";

import type { components } from "@/api/schema";
import { apiClient } from "@/api/client";
import { errorMessage, settle } from "@/api/errors";
import i18n from "@/i18n";
import type { ToastStore } from "@/stores/ToastStore";

export type Product = components["schemas"]["ProductResponse"];
export type ProductsOverview = components["schemas"]["ProductsOverviewResponse"];

/**
 * The products the user buys, matched across receipts and shops (F16.1): the list,
 * its search, the products ticked for merging, and merging and splitting them. The
 * server answers both with the list as it now is.
 */
export class ProductsStore {
  products: Product[] = [];
  search = "";
  selected: string[] = [];
  /** Every product seen in any answer, so a product ticked before a search keeps its name. */
  known = new Map<string, Product>();
  isLoading = false;
  isSaving = false;
  loadError: string | null = null;
  /** Price moves and shops over the last six months (F23.5); null until loaded. */
  overview: ProductsOverview | null = null;
  private requests = 0;
  private readonly toastStore: ToastStore;

  constructor(toastStore: ToastStore) {
    this.toastStore = toastStore;
    makeAutoObservable<this, "toastStore" | "requests">(
      this,
      { toastStore: false, requests: false },
      { autoBind: true },
    );
  }

  /** The products ticked, in the order they were ticked, found or not by the search. */
  get selectedProducts(): Product[] {
    return this.selected
      .map((id) => this.known.get(id))
      .filter((p): p is Product => p !== undefined);
  }

  /** A product by id, from whichever answer it last came in. */
  productById(id: string): Product | undefined {
    return this.known.get(id);
  }

  /** Ask for the list; a later request wins over an earlier one still on its way. */
  async load(): Promise<void> {
    const request = ++this.requests;
    this.isLoading = true;
    this.loadError = null;
    const response = await settle(() =>
      apiClient.GET("/api/v1/products", { params: { query: { search: this.search } } }),
    );
    runInAction(() => {
      if (request !== this.requests) return;
      this.isLoading = false;
      if (response.error) {
        this.loadError = errorMessage(response.error, i18n.t("messages:products.loadFailed"));
        return;
      }
      this.products = response.data;
      for (const product of response.data) this.known.set(product.id, product);
      // A search shows only some products: a ticked one it does not show stays ticked, so
      // several can be picked by searching for each. Only the whole list says one is gone.
      if (!this.search) {
        this.selected = this.selected.filter((id) => response.data.some((p) => p.id === id));
      }
    });
  }

  /** The six months' biggest price moves and each shop's standing; quiet on failure. */
  async loadOverview(today = new Date()): Promise<void> {
    const start = new Date(today.getFullYear(), today.getMonth() - 5, 1);
    const day = (d: Date) =>
      `${String(d.getFullYear())}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    const response = await settle(() =>
      apiClient.GET("/api/v1/products/overview", {
        params: { query: { start: day(start), end: day(today) } },
      }),
    );
    runInAction(() => {
      if (response.error === undefined) this.overview = response.data;
    });
  }

  setSearch(search: string): void {
    this.search = search;
    void this.load();
  }

  toggle(id: string): void {
    this.selected = this.selected.includes(id)
      ? this.selected.filter((s) => s !== id)
      : [...this.selected, id];
  }

  /** Tick exactly these products, as a saved selection asks. */
  select(ids: string[]): void {
    this.selected = [...ids];
  }

  clearSelection(): void {
    this.selected = [];
  }

  /** Fold the other ticked products into `targetId`, which keeps its name. */
  async merge(targetId: string): Promise<boolean> {
    const others = this.selected.filter((id) => id !== targetId);
    if (others.length === 0 || this.isSaving) return false;
    this.isSaving = true;
    const response = await settle(() =>
      apiClient.POST("/api/v1/products/{product_id}/merge", {
        params: { path: { product_id: targetId } },
        body: { product_ids: others },
      }),
    );
    return this.settleChange(response, i18n.t("messages:products.mergeFailed"), () => {
      this.selected = [];
      this.toastStore.showSuccess(i18n.t("messages:products.merged"));
    });
  }

  /** Take one way of printing out of a product into a product of its own. */
  async split(productId: string, aliasId: string): Promise<boolean> {
    if (this.isSaving) return false;
    this.isSaving = true;
    const response = await settle(() =>
      apiClient.POST("/api/v1/products/{product_id}/split", {
        params: { path: { product_id: productId } },
        body: { alias_id: aliasId },
      }),
    );
    return this.settleChange(response, i18n.t("messages:products.splitFailed"), () => {
      this.toastStore.showSuccess(i18n.t("messages:products.split"));
    });
  }

  private settleChange(
    response: { data?: Product[]; error?: unknown },
    fallback: string,
    done: () => void,
  ): boolean {
    const products = response.error ? undefined : response.data;
    runInAction(() => {
      this.isSaving = false;
      if (!products) {
        this.toastStore.showError(errorMessage(response.error, fallback));
        return;
      }
      // The answer is the whole list; while searching, the search is asked again instead.
      if (!this.search) this.products = products;
      this.known = new Map(products.map((product) => [product.id, product]));
      done();
    });
    if (products && this.search) void this.load();
    return products !== undefined;
  }

  /** Forget everything: a different user is signing in. */
  reset(): void {
    this.overview = null;
    this.products = [];
    this.search = "";
    this.selected = [];
    this.known = new Map();
    this.loadError = null;
  }
}
