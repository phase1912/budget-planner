import { describe, it, expect, vi, beforeEach } from "vitest";
import { ReceiptStore, changeMessage } from "./ReceiptStore";
import type { ReceiptDetail } from "./ReceiptStore";
import { ToastStore } from "./ToastStore";
import { apiClient } from "../api/client";

// Mock the API client
vi.mock("../api/client", () => ({
  apiClient: {
    GET: vi.fn(),
    PATCH: vi.fn(),
    DELETE: vi.fn(),
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

  it("names a finished month it recalculated, and tells the month view to refetch", async () => {
    const changed = vi.fn();
    const successSpy = vi.spyOn(toastStore, "showSuccess");
    const store = new ReceiptStore(toastStore, changed, () => new Date(2026, 8, 26));
    const before = { id: "r1", transaction_date: "2026-08-04T11:26:00Z" } as ReceiptDetail;
    store.receiptDetail = before;
    vi.mocked(apiClient.PATCH).mockResolvedValueOnce({
      data: { ...before, total_amount: "124.00" },
      response: new Response(),
    });
    vi.mocked(apiClient.GET).mockResolvedValueOnce({
      data: { items: [], total: 0, page: 1, size: 20, pages: 0 },
      response: new Response(),
    });

    await store.updateReceipt("r1", {} as never);

    expect(successSpy).toHaveBeenCalledWith("Receipt updated. August 2026 recalculated");
    expect(changed).toHaveBeenCalledOnce();
  });

  it("tells the month view to refetch after a delete", async () => {
    const changed = vi.fn();
    const store = new ReceiptStore(toastStore, changed);
    vi.mocked(apiClient.DELETE).mockResolvedValueOnce({ response: new Response() } as never);
    vi.mocked(apiClient.GET).mockResolvedValueOnce({
      data: { items: [], total: 0, page: 1, size: 20, pages: 0 },
      response: new Response(),
    });

    await store.deleteReceipt("r1");

    expect(changed).toHaveBeenCalledOnce();
  });

  it("does not refetch the month when a save fails", async () => {
    const changed = vi.fn();
    const store = new ReceiptStore(toastStore, changed);
    vi.mocked(apiClient.PATCH).mockResolvedValueOnce({
      error: { detail: "Line totals do not add up" },
      response: new Response(),
    } as never);

    await store.updateReceipt("r1", {} as never);

    expect(changed).not.toHaveBeenCalled();
  });
});

describe("changeMessage", () => {
  const SEPT_26 = new Date(2026, 8, 26);
  const dated = (transaction_date: string | null, created_at = "2026-09-20T10:00:00Z") => ({
    transaction_date,
    created_at,
  });

  it("says nothing extra about a month still running", () => {
    expect(changeMessage("Receipt updated", [dated("2026-09-24T10:47:00Z")], SEPT_26)).toBe(
      "Receipt updated",
    );
  });

  it("names both months when a receipt moves between them, in calendar order", () => {
    expect(
      changeMessage(
        "Receipt updated",
        [dated("2026-08-31T23:30:00Z"), dated("2026-07-02T09:00:00Z")],
        SEPT_26,
      ),
    ).toBe("Receipt updated. July 2026 and August 2026 recalculated");
  });

  it("files an undated receipt under its upload date, like the month total", () => {
    expect(changeMessage("Receipt deleted", [dated(null, "2026-08-20T09:00:00Z")], SEPT_26)).toBe(
      "Receipt deleted. August 2026 recalculated",
    );
  });
});
