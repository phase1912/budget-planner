import { describe, it, expect, vi, beforeEach } from "vitest";
import { ReceiptStore } from "./ReceiptStore";
import { ToastStore } from "./ToastStore";
import { apiClient } from "../api/client";

// Mock the API client
vi.mock("../api/client", () => ({
  apiClient: {
    GET: vi.fn(),
  },
}));

describe("ReceiptStore", () => {
  let store: ReceiptStore;
  let toastStore: ToastStore;

  let showErrorSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    toastStore = new ToastStore();
    showErrorSpy = vi.spyOn(toastStore, "showError");
    store = new ReceiptStore(toastStore);
    vi.clearAllMocks();
  });

  it("fetches receipts successfully", async () => {
    const mockData = {
      items: [{ id: "r1", merchant_name: "Tesco", total_amount: "10.00", status: "parsed" }],
      total: 1,
      page: 1,
      size: 20,
      pages: 1,
    };

    vi.mocked(apiClient.GET).mockResolvedValueOnce({
      data: mockData,
      response: new Response(),
    });

    await store.fetchReceipts(1, 20);

    expect(apiClient.GET).toHaveBeenCalledWith("/receipts", {
      params: { query: { page: 1, size: 20 } },
    });
    expect(store.receipts).toEqual(mockData.items);
    expect(store.total).toBe(1);
    expect(store.isLoadingList).toBe(false);
    expect(store.listError).toBeNull();
  });

  it("handles fetch receipts failure", async () => {
    vi.mocked(apiClient.GET).mockResolvedValueOnce({
      // @ts-expect-error mock response structure
      error: { detail: [{ msg: "Failed" }] },
      response: new Response(),
    });

    await store.fetchReceipts(1, 20);

    expect(store.listError).toBe("Failed");
    expect(store.isLoadingList).toBe(false);
    expect(showErrorSpy).toHaveBeenCalledWith("Failed");
  });

  it("fetches receipt detail successfully", async () => {
    const mockData = {
      id: "r1",
      merchant_name: "Tesco",
      total_amount: "10.00",
      status: "parsed",
      line_items: [],
    };

    vi.mocked(apiClient.GET).mockResolvedValueOnce({
      data: mockData,
      response: new Response(),
    });

    await store.fetchReceiptDetail("r1");

    expect(apiClient.GET).toHaveBeenCalledWith("/receipts/{receipt_id}", {
      params: { path: { receipt_id: "r1" } },
    });
    expect(store.selectedReceiptId).toBe("r1");
    expect(store.receiptDetail).toEqual(mockData);
    expect(store.isLoadingDetail).toBe(false);
    expect(store.detailError).toBeNull();
  });

  it("handles fetch receipt detail failure", async () => {
    vi.mocked(apiClient.GET).mockResolvedValueOnce({
      // @ts-expect-error mock response structure
      error: { detail: [{ msg: "Not Found" }] },
      response: new Response(),
    });

    await store.fetchReceiptDetail("r1");

    expect(store.detailError).toBe("Not Found");
    expect(store.isLoadingDetail).toBe(false);
    expect(showErrorSpy).toHaveBeenCalledWith("Not Found");
  });

  it("clears selection", () => {
    store.selectedReceiptId = "r1";
    store.receiptDetail = { id: "r1" } as never;

    store.clearSelection();

    expect(store.selectedReceiptId).toBeNull();
    expect(store.receiptDetail).toBeNull();
  });

  it("updates filters and fetches receipts on page 1", async () => {
    vi.mocked(apiClient.GET).mockResolvedValue({
      data: { items: [], total: 0, page: 1, size: 20, pages: 0 },
      response: new Response(),
    });

    store.page = 3; // Ensure page resets to 1

    store.setFilters({
      status: "uploaded",
      startDate: "2025-01-01T00:00:00Z",
      endDate: "2025-12-31T23:59:59Z",
      searchQuery: "apple",
    });

    // Should fetch with new filters
    expect(store.page).toBe(1);
    expect(store.statusFilter).toBe("uploaded");
    expect(store.startDateFilter).toBe("2025-01-01T00:00:00Z");
    expect(store.searchQuery).toBe("apple");

    // Wait for the async fetch to be called
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(apiClient.GET).toHaveBeenCalledWith("/receipts", {
      params: {
        query: {
          page: 1,
          size: 20,
          status: "uploaded",
          start_date: "2025-01-01T00:00:00Z",
          end_date: "2025-12-31T23:59:59Z",
          q: "apple",
        },
      },
    });
  });

  it("clearing a filter removes it from the query", async () => {
    store.statusFilter = "parsed";
    vi.mocked(apiClient.GET).mockResolvedValue({
      data: { items: [], total: 0, page: 1, size: 20, pages: 0 },
      response: new Response(),
    });

    // Clear status
    store.setFilters({ status: undefined });

    expect(store.statusFilter).toBeUndefined();

    // Wait for the async fetch to be called
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(apiClient.GET).toHaveBeenCalledWith("/receipts", {
      params: {
        query: {
          page: 1,
          size: 20,
        },
      },
    });
  });
});
