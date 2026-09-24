import { makeAutoObservable, runInAction } from "mobx";

import type { components } from "@/api/schema";
import { apiClient } from "@/api/client";
import { errorMessage } from "@/api/errors";

const UNCATEGORIZED = "Uncategorized";

export type Category = components["schemas"]["CategoryOut"];
export type ReviewQueueItem = components["schemas"]["ReviewQueueItemResponse"];
export type ItemView = components["schemas"]["ItemView"];

const SEARCH_DEBOUNCE_MS = 250;

/**
 * Holds the category taxonomy for the current user (BRD C1, C2).
 *
 * Fetches both built-in and custom categories with their aggregated
 * item_count and total_amount from the backend.
 */
export class CategoriesStore {
  categories: Category[] = [];
  isLoading = false;
  error: string | null = null;

  reviewQueue: ReviewQueueItem[] = [];
  isLoadingQueue = false;
  queueError: string | null = null;
  queueView: ItemView = "needs_review";
  queueSearch = "";
  needsReviewCount = 0;

  private queueRequest = 0;
  private searchTimer: ReturnType<typeof setTimeout> | undefined;

  constructor() {
    makeAutoObservable(this, {}, { autoBind: true });
  }

  /** Built-in categories (user_id is NULL on the backend). */
  get builtInCategories(): Category[] {
    return this.categories.filter((c) => c.is_builtin);
  }

  /** User-defined custom categories. */
  get customCategories(): Category[] {
    return this.categories.filter((c) => !c.is_builtin);
  }

  /**
   * Categories an owner can file an item under by hand (BRD C4).
   *
   * Uncategorized is the absence of a decision, not one to make: choosing it
   * would leave the item in the review queue for good.
   */
  get assignableBuiltIns(): Category[] {
    return this.builtInCategories.filter((c) => c.name !== UNCATEGORIZED);
  }

  /** Whether a category id is the Uncategorized fallback (or no category at all). */
  isUncategorized(categoryId: string | null | undefined): boolean {
    if (!categoryId) return true;
    return this.categories.find((c) => c.id === categoryId)?.name === UNCATEGORIZED;
  }

  /**
   * Load the taxonomy once for however many pickers are on screen.
   *
   * Every picker in a list calls this on mount; only the first one fetches.
   */
  ensureCategories(): void {
    if (this.categories.length > 0 || this.isLoading) return;
    void this.fetchCategories();
  }

  /**
   * File one line item under the category its owner chose (BRD C4).
   *
   * Resolves to null on success, or to a message the caller can show.
   */
  async reassignCategory(itemId: string, categoryId: string): Promise<string | null> {
    const response = await apiClient.PATCH("/receipts/line-items/{item_id}/category", {
      params: { path: { item_id: itemId } },
      body: { category_id: categoryId },
    });
    return response.error ? errorMessage(response.error, "Could not change the category") : null;
  }

  /**
   * Fetch all categories with statistics from the backend.
   *
   * Called when the categories page mounts. A fresh call replaces whatever
   * the store held before, so navigating away and back always shows
   * up-to-date totals.
   */
  async fetchCategories(): Promise<void> {
    this.isLoading = true;
    this.error = null;

    try {
      const response = await apiClient.GET("/api/v1/categories");

      if (response.error) {
        throw new Error(errorMessage(response.error, "Failed to fetch categories"));
      }

      runInAction(() => {
        this.categories = response.data;
        this.isLoading = false;
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      runInAction(() => {
        this.error = message;
        this.isLoading = false;
      });
    }
  }

  /**
   * Fetch the current view of the categorisation screen, oldest purchase first (BRD C3, C4).
   *
   * The server decides what belongs in each view; this only mirrors it. A
   * response that arrives after a newer request was made is dropped, so fast
   * tab switching or typing never shows a stale list.
   */
  async fetchReviewQueue(): Promise<void> {
    const request = ++this.queueRequest;
    this.isLoadingQueue = true;
    this.queueError = null;

    try {
      const response = await apiClient.GET("/receipts/line-items", {
        params: { query: { view: this.queueView, q: this.queueSearch.trim() || undefined } },
      });
      if (response.error) {
        throw new Error(errorMessage(response.error, "Failed to fetch review queue"));
      }
      if (request !== this.queueRequest) return;
      runInAction(() => {
        this.reviewQueue = response.data.items;
        this.needsReviewCount = response.data.needs_review_count;
        this.isLoadingQueue = false;
      });
    } catch (error) {
      if (request !== this.queueRequest) return;
      const message = error instanceof Error ? error.message : "Unknown error";
      runInAction(() => {
        this.queueError = message;
        this.isLoadingQueue = false;
      });
    }
  }

  /** Switch between "Needs review", "Corrected by you" and "All items". */
  setQueueView(view: ItemView): void {
    if (view === this.queueView) return;
    this.queueView = view;
    void this.fetchReviewQueue();
  }

  /** Narrow the current view by item name, once the user pauses typing. */
  setQueueSearch(search: string): void {
    this.queueSearch = search;
    clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => {
      void this.fetchReviewQueue();
    }, SEARCH_DEBOUNCE_MS);
  }
}
