import { makeAutoObservable, runInAction } from "mobx";

import type { components } from "@/api/schema";
import { apiClient } from "@/api/client";
import { errorMessage, settle } from "@/api/errors";
import i18n from "@/i18n";
import { presetDays } from "@/stores/StatisticsStore";
import type { ToastStore } from "@/stores/ToastStore";

export type Exploration = components["schemas"]["ExplorationResponse"];
export type Selection = components["schemas"]["SelectionResponse"];
export type ExplorePreset =
  "this_month" | "last_month" | "last_3_months" | "last_6_months" | "all" | "custom";

/**
 * Exploring what the user buys (F16.2): the ticked products over a period — how much,
 * what it cost, month by month, and per shop — and the selections saved under a name.
 * A later request wins over an earlier one still on its way.
 */
export class ExplorationStore {
  productIds: string[] = [];
  /** All time first: one product's whole story, not just this month's few purchases. */
  preset: ExplorePreset = "all";
  start: string | null = null;
  end: string | null = null;
  result: Exploration | null = null;
  isLoading = false;
  error: string | null = null;
  selections: Selection[] = [];
  isSaving = false;
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

  /**
   * The saved selection holding exactly these products, in any order, if one does: what
   * is ticked is then already saved, so saving it again is not offered.
   */
  selectionMatching(productIds: readonly string[]): Selection | undefined {
    const ticked = new Set(productIds);
    return this.selections.find(
      (selection) =>
        selection.product_ids.length === ticked.size &&
        selection.product_ids.every((id) => ticked.has(id)),
    );
  }

  /** Explore these products; an empty list clears the result. */
  setProducts(ids: string[]): void {
    this.productIds = ids;
    void this.load();
  }

  choosePreset(preset: Exclude<ExplorePreset, "custom">): void {
    this.preset = preset;
    [this.start, this.end] = preset === "all" ? [null, null] : presetDays(preset, new Date());
    void this.load();
  }

  chooseRange(start: string, end: string): void {
    this.preset = "custom";
    this.start = start;
    this.end = end;
    void this.load();
  }

  async load(): Promise<void> {
    const request = ++this.requests;
    if (this.productIds.length === 0) {
      this.result = null;
      this.isLoading = false;
      return;
    }
    this.isLoading = true;
    this.error = null;
    const period = this.start && this.end ? { start: this.start, end: this.end } : {};
    const response = await settle(() =>
      apiClient.GET("/api/v1/products/explore", {
        params: { query: { product_ids: this.productIds, ...period } },
      }),
    );
    runInAction(() => {
      if (request !== this.requests) return;
      this.isLoading = false;
      if (response.error) {
        this.error = errorMessage(response.error, i18n.t("messages:products.exploreFailed"));
        return;
      }
      this.result = response.data;
    });
  }

  async loadSelections(): Promise<void> {
    const response = await settle(() => apiClient.GET("/api/v1/products/selections"));
    runInAction(() => {
      if (!response.error) this.selections = response.data;
    });
  }

  /** Save the ticked products under a name; true when saved. */
  async saveSelection(name: string): Promise<boolean> {
    if (this.isSaving || this.productIds.length === 0) return false;
    this.isSaving = true;
    const response = await settle(() =>
      apiClient.POST("/api/v1/products/selections", {
        body: { name, product_ids: this.productIds },
      }),
    );
    runInAction(() => {
      this.isSaving = false;
      if (response.error) {
        this.toastStore.showError(
          errorMessage(response.error, i18n.t("messages:products.saveSelectionFailed")),
        );
        return;
      }
      this.selections = [...this.selections, response.data].sort((a, b) =>
        a.name.localeCompare(b.name),
      );
      this.toastStore.showSuccess(i18n.t("messages:products.selectionSaved"));
    });
    return response.error === undefined;
  }

  async deleteSelection(id: string): Promise<void> {
    const response = await settle(() =>
      apiClient.DELETE("/api/v1/products/selections/{selection_id}", {
        params: { path: { selection_id: id } },
      }),
    );
    runInAction(() => {
      if (response.error) {
        this.toastStore.showError(
          errorMessage(response.error, i18n.t("messages:products.deleteSelectionFailed")),
        );
        return;
      }
      this.selections = this.selections.filter((s) => s.id !== id);
    });
  }

  /** Forget everything: a different user is signing in. */
  reset(): void {
    this.productIds = [];
    this.result = null;
    this.selections = [];
    this.error = null;
    this.choosePreset("this_month");
  }
}
