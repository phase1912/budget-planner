import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/api/client";
import { ExportStore } from "./ExportStore";
import type { ToastStore } from "./ToastStore";

vi.mock("@/api/client", () => ({ apiClient: { GET: vi.fn(), POST: vi.fn() } }));

const REQUEST = {
  kind: "statistics",
  format: "csv",
  start: "2026-09-01",
  end: "2026-09-27",
  compare: true,
} as const;

function job(status: string, error: string | null = null) {
  return {
    id: "job-1",
    kind: "statistics",
    format: "csv",
    status,
    filename: "statistics-2026-09-01_2026-09-27.csv",
    error,
    created_at: "2026-09-27T10:00:00Z",
    completed_at: null,
  };
}

const ok = (data: unknown) => ({ data, response: new Response() });

describe("ExportStore", () => {
  let toast: { showSuccess: ReturnType<typeof vi.fn>; showError: ReturnType<typeof vi.fn> };
  let save: ReturnType<typeof vi.fn<(file: Blob, filename: string) => void>>;
  let store: ExportStore;

  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(apiClient.GET).mockReset();
    vi.mocked(apiClient.POST).mockReset();
    toast = { showSuccess: vi.fn(), showError: vi.fn() };
    save = vi.fn<(file: Blob, filename: string) => void>();
    store = new ExportStore(toast as unknown as ToastStore, save);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("follows the background export until it is ready, then saves the file under its name", async () => {
    const file = new Blob(["category,total\n"]);
    vi.mocked(apiClient.POST).mockResolvedValue(ok(job("pending")));
    vi.mocked(apiClient.GET)
      .mockResolvedValueOnce(ok(job("running")))
      .mockResolvedValueOnce(ok(job("ready")))
      .mockResolvedValueOnce(ok(file));

    const done = store.start(REQUEST);
    expect(store.busy.statistics).toBe(true);
    await vi.runAllTimersAsync();
    await done;

    expect(apiClient.POST).toHaveBeenCalledWith("/api/v1/exports", { body: REQUEST });
    expect(save).toHaveBeenCalledWith(file, "statistics-2026-09-01_2026-09-27.csv");
    expect(toast.showSuccess).toHaveBeenCalledWith("Exported statistics-2026-09-01_2026-09-27.csv");
    expect(store.busy.statistics).toBe(false);
  });

  it("says why an export failed and frees the button again", async () => {
    vi.mocked(apiClient.POST).mockResolvedValue(ok(job("pending")));
    vi.mocked(apiClient.GET).mockResolvedValueOnce(
      ok(job("failed", "The export could not be written. Try again.")),
    );

    const done = store.start(REQUEST);
    await vi.runAllTimersAsync();
    await done;

    expect(toast.showError).toHaveBeenCalledWith("The export could not be written. Try again.");
    expect(save).not.toHaveBeenCalled();
    expect(store.busy.statistics).toBe(false);
  });

  it("reports a refused request, such as a period ending before it starts", async () => {
    vi.mocked(apiClient.POST).mockResolvedValue({
      error: { detail: "The period ends before it starts" },
      response: new Response(),
    });

    await store.start(REQUEST);

    expect(toast.showError).toHaveBeenCalledWith("The period ends before it starts");
    expect(apiClient.GET).not.toHaveBeenCalled();
  });
});
