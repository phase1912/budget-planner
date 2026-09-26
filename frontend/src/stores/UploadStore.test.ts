import { describe, it, expect, vi, beforeEach } from "vitest";
import { UploadStore, totalNeedsDecision } from "./UploadStore";
import type { ApiClient } from "@/api/client";
import type { ToastStore } from "./ToastStore";

describe("UploadStore", () => {
  let mockApi: unknown;
  let store: UploadStore;

  beforeEach(() => {
    mockApi = {
      POST: vi.fn(),
      GET: vi.fn(),
    };

    store = new UploadStore(mockApi as ApiClient);
  });

  it("should initialize with default state", () => {
    expect(store.uploadState.status).toBe("idle");
    expect(store.errorTitle).toBeNull();
    expect(store.errorDetails).toBeNull();
  });

  it("should handle successful upload", async () => {
    (mockApi as { POST: ReturnType<typeof vi.fn> }).POST.mockResolvedValue({
      data: { message: "File accepted", job_id: "test-job-id" },
      error: undefined,
      response: { status: 200 },
    });

    (mockApi as { GET: ReturnType<typeof vi.fn> }).GET.mockResolvedValue({
      data: { status: "completed", file_ids: ["file1"] },
      error: undefined,
      response: { status: 200 },
    });

    const file = new File(["dummy content"], "test.png", { type: "image/png" });
    const success = await store.uploadFile(file);

    expect(success).toBe(true);
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(store.uploadState.status).toBe("success");
    expect(store.errorTitle).toBeNull();
  });

  it("should handle 415 unsupported format error", async () => {
    (mockApi as { POST: ReturnType<typeof vi.fn> }).POST.mockResolvedValue({
      data: undefined,
      error: {
        title: "Unsupported Media Type",
        detail: "Only JPEG, PNG, HEIC and PDF are supported.",
      },
      response: { status: 415 },
    });

    const file = new File(["dummy content"], "test.txt", { type: "text/plain" });
    const success = await store.uploadFile(file);

    expect(success).toBe(false);
    expect(store.uploadState.status).toBe("error");
    expect(store.errorTitle).toBe("Unsupported Media Type");
    expect(store.errorDetails).toBe("Only JPEG, PNG, HEIC and PDF are supported.");
  });

  it("counts an unreadable total as one decision, however it is flagged", () => {
    store.extractedData = {
      extractions: [
        { requires_manual_review: true, receipt_total: null, receipt_total_confidence: 0 },
        { receipt_total: "12.00", receipt_total_confidence: 40 },
        { receipt_total: "9.00", receipt_total_confidence: 95 },
      ],
    };
    store.selectedIndices = new Set([0, 1, 2]);

    expect(store.conflictsCount).toBe(2);
  });
});

describe("UploadStore surfaces what the server refused", () => {
  function storeWith(POST: ReturnType<typeof vi.fn>) {
    const showError = vi.fn();
    const showSuccess = vi.fn();
    const stored = vi.fn();
    const store = new UploadStore(
      { POST, GET: vi.fn() } as unknown as ApiClient,
      { showError, showSuccess } as unknown as ToastStore,
      stored,
    );
    store.jobId = "job-1";
    store.selectedIndices = new Set([0]);
    return { store, showError, showSuccess, stored };
  }

  it("shows why a commit was refused, stays on the page and can be retried", async () => {
    const POST = vi.fn().mockResolvedValue({
      error: { detail: "Extraction 0 requires manual review" },
      response: { status: 400 },
    });
    const { store, showError } = storeWith(POST);
    store.currentStep = 2;

    expect(await store.commitJob()).toBe(false);

    expect(showError).toHaveBeenCalledWith("Extraction 0 requires manual review");
    expect(store.currentStep).toBe(2);
    expect(store.jobId).toBe("job-1");
    expect(store.isCommitting).toBe(false);
  });

  it("stores once however often the button is pressed", async () => {
    let finish: (value: unknown) => void = () => undefined;
    const POST = vi.fn().mockReturnValue(
      new Promise((resolve) => {
        finish = resolve;
      }),
    );
    const { store } = storeWith(POST);

    const first = store.commitJob();
    expect(await store.commitJob()).toBe(false);
    finish({ data: {}, response: { status: 200 } });
    expect(await first).toBe(true);
    expect(POST).toHaveBeenCalledTimes(1);
  });

  it("after storing, starts afresh on an empty first step for the next receipt", async () => {
    const POST = vi.fn().mockResolvedValue({ data: {}, response: { status: 200 } });
    const { store, showSuccess } = storeWith(POST);
    const photo = new File(["x"], "pepco-1.jpg", { type: "image/jpeg" });
    store.lines = [[photo, photo, photo]];
    store.mode = "multiple";
    store.currentStep = 2;
    store.extractedData = { extractions: [{ merchant_name: "pepco" }] };

    expect(await store.commitJob()).toBe(true);

    expect(store.lines).toEqual([[]]);
    expect(store.mode).toBe("single");
    expect(store.currentStep).toBe(1);
    expect(store.jobId).toBeNull();
    expect(store.extractedData).toBeNull();
    expect(showSuccess).toHaveBeenCalledWith("1 receipt stored");
  });

  it("tells the month view to refetch once receipts are stored, and not when refused", async () => {
    const stored = storeWith(vi.fn().mockResolvedValue({ data: {}, response: { status: 200 } }));
    await stored.store.commitJob();
    expect(stored.stored).toHaveBeenCalledOnce();

    const refused = storeWith(
      vi.fn().mockResolvedValue({ error: { detail: "No" }, response: { status: 400 } }),
    );
    await refused.store.commitJob();
    expect(refused.stored).not.toHaveBeenCalled();
  });

  it("counts only the receipts actually stored, not skipped duplicates", () => {
    const { store } = storeWith(vi.fn());
    store.extractedData = {
      extractions: [{}, { duplicate_resolved: "skipped", is_skipped: true }, {}],
    };
    store.selectedIndices = new Set([0, 1, 2]);
    expect(store.receiptsToStore).toBe(2);
  });

  it("going back to the photos keeps them for another try", () => {
    const { store } = storeWith(vi.fn());
    const photo = new File(["x"], "pepco-1.jpg", { type: "image/jpeg" });
    store.lines = [[photo]];
    store.currentStep = 2;

    store.resetData();

    expect(store.lines).toEqual([[photo]]);
    expect(store.currentStep).toBe(1);
  });

  it("shows why a duplicate decision was refused", async () => {
    const POST = vi.fn().mockResolvedValue({ error: { detail: "Job not found" } });
    const { store, showError } = storeWith(POST);

    expect(await store.resolveDuplicate(0, "store")).toBe(false);
    expect(showError).toHaveBeenCalledWith("Job not found");
  });
});

describe("totalNeedsDecision", () => {
  it("wants a total that is missing or read with low confidence, and nothing else", () => {
    expect(totalNeedsDecision({ receipt_total: null })).toBe(true);
    expect(totalNeedsDecision({ receipt_total: "5.00", receipt_total_confidence: 79 })).toBe(true);
    expect(totalNeedsDecision({ receipt_total: "5.00", receipt_total_confidence: 80 })).toBe(false);
    expect(totalNeedsDecision({ receipt_total: "5.00" })).toBe(false);
  });
});
