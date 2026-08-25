import { describe, it, expect, vi, beforeEach } from "vitest";
import { UploadStore } from "./UploadStore";
import type { ApiClient } from "@/api/client";

describe("UploadStore", () => {
  let mockApi: unknown;
  let store: UploadStore;

  beforeEach(() => {
    mockApi = {
      POST: vi.fn(),
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
      data: { message: "File accepted" },
      error: undefined,
      response: { status: 200 },
    });

    const file = new File(["dummy content"], "test.png", { type: "image/png" });
    const success = await store.uploadFile(file);

    expect(success).toBe(true);
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
});
