import { makeAutoObservable, runInAction } from "mobx";

import type { components } from "@/api/schema";
import { apiClient } from "@/api/client";
import { errorMessage } from "@/api/errors";

export type Category = components["schemas"]["CategoryOut"];
export type ReviewQueueItem = components["schemas"]["ReviewQueueItemResponse"];

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
   * Fetch the line items filed under Uncategorized, oldest purchase first (BRD C3).
   *
   * The server decides what belongs in the queue; this only mirrors it.
   */
  async fetchReviewQueue(): Promise<void> {
    this.isLoadingQueue = true;
    this.queueError = null;

    try {
      const response = await apiClient.GET("/receipts/line-items/review", {});

      if (response.error) {
        throw new Error(errorMessage(response.error, "Failed to fetch review queue"));
      }

      runInAction(() => {
        this.reviewQueue = response.data;
        this.isLoadingQueue = false;
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      runInAction(() => {
        this.queueError = message;
        this.isLoadingQueue = false;
      });
    }
  }
}
