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
