import { describe, it, expect, vi, beforeEach } from "vitest";
import { CategoriesStore } from "./CategoriesStore";
import { apiClient } from "../api/client";

vi.mock("../api/client", () => ({
  apiClient: {
    GET: vi.fn(),
  },
}));

describe("CategoriesStore", () => {
  let store: CategoriesStore;

  beforeEach(() => {
    store = new CategoriesStore();
    vi.clearAllMocks();
  });

  it("fetches categories successfully", async () => {
    const mockData = [
      { id: "1", name: "Groceries", is_builtin: true, item_count: 5, total_amount: "150.00" },
      { id: "2", name: "Hobbies", is_builtin: false, item_count: 1, total_amount: "50.00" },
    ];

    vi.mocked(apiClient.GET).mockResolvedValueOnce({
      data: mockData,
      response: new Response(),
    });

    await store.fetchCategories();

    expect(store.isLoading).toBe(false);
    expect(store.error).toBeNull();
    expect(store.categories.length).toBe(2);
    expect(store.builtInCategories.length).toBe(1);
    expect(store.customCategories.length).toBe(1);
  });

  it("handles fetch errors", async () => {
    vi.mocked(apiClient.GET).mockResolvedValueOnce({
      // @ts-expect-error mock response structure
      error: { detail: "Database error" },
      response: new Response(),
    });

    await store.fetchCategories();

    expect(store.isLoading).toBe(false);
    expect(store.error).toBe("Database error");
    expect(store.categories.length).toBe(0);
  });

  it("handles network errors", async () => {
    vi.mocked(apiClient.GET).mockRejectedValueOnce(new Error("Network failure"));

    await store.fetchCategories();

    expect(store.isLoading).toBe(false);
    expect(store.error).toBe("Network failure");
  });
});

describe("CategoriesStore review queue paging", () => {
  function page(items: unknown[], pages: number, total: number) {
    return {
      data: { items, pages, total, page: 1, size: 20, needs_review_count: total },
      response: new Response(),
    };
  }

  beforeEach(() => {
    vi.mocked(apiClient.GET).mockReset();
  });

  it("goes back to the first page when the view or dates change", async () => {
    vi.mocked(apiClient.GET).mockResolvedValue(page([], 0, 0));
    const store = new CategoriesStore();
    store.setQueuePage(3);
    store.setQueueView("all");
    expect(store.queuePage).toBe(1);

    store.setQueuePage(2);
    store.setQueueDates("2026-07-01T00:00:00Z", "2026-07-31T23:59:59Z");
    expect(store.queuePage).toBe(1);
    await vi.waitFor(() => {
      expect(apiClient.GET).toHaveBeenLastCalledWith("/receipts/line-items", {
        params: {
          query: expect.objectContaining({
            view: "all",
            start_date: "2026-07-01T00:00:00Z",
            end_date: "2026-07-31T23:59:59Z",
            page: 1,
          }) as unknown,
        },
      });
    });
  });

  it("steps back when filing the last item empties the last page", async () => {
    vi.mocked(apiClient.GET)
      .mockResolvedValueOnce(page([], 2, 40))
      .mockResolvedValueOnce(page([{ id: "x" }], 2, 40));
    const store = new CategoriesStore();
    store.queuePage = 3;

    await store.fetchReviewQueue();

    expect(store.queuePage).toBe(2);
    expect(store.reviewQueue).toHaveLength(1);
  });
});
