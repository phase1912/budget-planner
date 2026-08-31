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
});
