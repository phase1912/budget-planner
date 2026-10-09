import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { UploadPage } from "./UploadPage";
import { StoreProvider } from "@/stores/StoreContext";
import { UploadStore } from "@/stores/UploadStore";
import { QuotaStore } from "@/stores/QuotaStore";
import type { ReceiptQuota } from "@/stores/QuotaStore";
import type { ApiClient } from "@/api/client";
import type { RootStore } from "@/stores/RootStore";

// The page asks for the quota on mount; left pending, the quota a test sets stays put.
vi.mock("@/api/client", () => ({ apiClient: { GET: vi.fn(() => new Promise(() => undefined)) } }));

function quotaStore(quota: ReceiptQuota | null = null): QuotaStore {
  const store = new QuotaStore();
  store.quota = quota;
  return store;
}

const QUOTA: ReceiptQuota = {
  limit: 10,
  used: 3,
  remaining: 7,
  unlimited: false,
  resets_on: "2026-11-01",
};

describe("UploadPage", () => {
  it("renders the upload button in idle state", () => {
    const mockApi = { POST: vi.fn() };
    const uploadStore = new UploadStore(mockApi as unknown as ApiClient);

    const mockStores = { uploadStore, quotaStore: quotaStore() } as unknown as RootStore;

    render(
      <StoreProvider store={mockStores}>
        <UploadPage />
      </StoreProvider>,
    );

    expect(screen.getByText("Add a receipt")).toBeInTheDocument();
  });

  it("renders the error panel when there is an error", () => {
    const mockApi = { POST: vi.fn() };
    const uploadStore = new UploadStore(mockApi as unknown as ApiClient);
    uploadStore.uploadState.fail("Test Error");
    uploadStore.errorTitle = "Unsupported file";
    uploadStore.errorDetails = "This file type is not supported.";

    const mockStores = { uploadStore, quotaStore: quotaStore() } as unknown as RootStore;

    render(
      <StoreProvider store={mockStores}>
        <UploadPage />
      </StoreProvider>,
    );

    expect(screen.getByText("Unsupported file")).toBeInTheDocument();
    expect(screen.getByText("This file type is not supported.")).toBeInTheDocument();
  });

  function renderWith(quota: ReceiptQuota, receipts = 1) {
    const uploadStore = new UploadStore({ POST: vi.fn() } as unknown as ApiClient);
    uploadStore.lines = Array.from({ length: receipts }, () => [
      new File(["x"], "r.jpg", { type: "image/jpeg" }),
    ]);
    const stores = { uploadStore, quotaStore: quotaStore(quota) } as unknown as RootStore;
    render(
      <StoreProvider store={stores}>
        <UploadPage />
      </StoreProvider>,
    );
  }

  it("says how many receipts are left this month", () => {
    renderWith(QUOTA);
    expect(screen.getByText("7 of 10 receipts left this month.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Read these photos/ })).toBeEnabled();
  });

  it("past the limit says when it resets and holds the upload", () => {
    renderWith({ ...QUOTA, used: 10, remaining: 0 });
    expect(screen.getByText(/used all 10 receipts this month.*1 November/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Read these photos/ })).toBeDisabled();
  });

  it("says how many to remove when a batch needs more than are left", () => {
    renderWith({ ...QUOTA, used: 8, remaining: 2 }, 3);
    expect(screen.getByText(/Only 2 receipts left.*Remove 1/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Read these photos/ })).toBeDisabled();
  });

  it("tells an admin there is no limit", () => {
    renderWith({ ...QUOTA, limit: null, remaining: null, unlimited: true });
    expect(screen.getByText("No receipt limit on this account.")).toBeInTheDocument();
  });
});
