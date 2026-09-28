import { makeAutoObservable, runInAction } from "mobx";

import type { components } from "@/api/schema";
import { apiClient } from "@/api/client";
import { errorMessage } from "@/api/errors";
import type { ToastStore } from "./ToastStore";

export type ExportRequest = components["schemas"]["ExportRequest"];
export type ExportKind = ExportRequest["kind"];
export type ExportFormat = ExportRequest["format"];
type ExportJob = components["schemas"]["ExportJobResponse"];

/** How often a running export is asked about, and for how long before giving up. */
const POLL_MS = 1000;
const GIVE_UP_AFTER = 120;

const wait = (ms: number) =>
  new Promise<void>((resolve) => {
    setTimeout(resolve, ms);
  });

/**
 * Exports of the user's receipts and statistics, as CSV or JSON (BRD N6 — F7.6).
 *
 * The server writes the file in the background, so starting one returns at
 * once: this store follows the job until it is ready, then downloads the file
 * and saves it under the export's name. One export per kind runs at a time;
 * the screen asking for it shows it as busy meanwhile.
 */
export class ExportStore {
  /** Which kinds have an export being written right now. */
  busy: Partial<Record<ExportKind, boolean>> = {};

  private readonly toastStore: ToastStore;
  private readonly save: (file: Blob, filename: string) => void;

  /** `save` hands the finished file to the browser; injectable so tests need no DOM download. */
  constructor(toastStore: ToastStore, save: (file: Blob, filename: string) => void = saveFile) {
    this.toastStore = toastStore;
    this.save = save;
    makeAutoObservable<this, "toastStore" | "save">(
      this,
      { toastStore: false, save: false },
      { autoBind: true },
    );
  }

  /** Export what a screen shows, in `format`; resolves once the file is saved or the export failed. */
  async start(request: ExportRequest): Promise<void> {
    if (this.busy[request.kind]) return;
    this.busy[request.kind] = true;
    try {
      const started = await apiClient.POST("/api/v1/exports", { body: request });
      if (started.error) {
        throw new Error(errorMessage(started.error, "The export could not be started"));
      }
      const job = await this.follow(started.data);
      const file = await apiClient.GET("/api/v1/exports/{job_id}/file", {
        params: { path: { job_id: job.id } },
        parseAs: "blob",
      });
      if (file.error) {
        throw new Error(errorMessage(file.error, "The export could not be downloaded"));
      }
      this.save(file.data, job.filename);
      this.toastStore.showSuccess(`Exported ${job.filename}`);
    } catch (error) {
      this.toastStore.showError(error instanceof Error ? error.message : "The export failed");
    } finally {
      runInAction(() => {
        this.busy[request.kind] = false;
      });
    }
  }

  /** Ask about the job until it is ready; a failed or stalled export is an error. */
  private async follow(job: ExportJob): Promise<ExportJob> {
    let current = job;
    for (let asked = 0; current.status !== "ready"; asked++) {
      if (current.status === "failed") throw new Error(current.error ?? "The export failed");
      if (asked >= GIVE_UP_AFTER) throw new Error("The export is taking too long. Try again.");
      await wait(POLL_MS);
      const polled = await apiClient.GET("/api/v1/exports/{job_id}", {
        params: { path: { job_id: current.id } },
      });
      if (polled.error) throw new Error(errorMessage(polled.error, "The export was lost"));
      current = polled.data;
    }
    return current;
  }
}

/** Save a file the way a download link would, under its own name. */
function saveFile(file: Blob, filename: string): void {
  const url = URL.createObjectURL(file);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
