import { makeAutoObservable, runInAction } from "mobx";
import type { ToastStore } from "./ToastStore";
import { errorMessage } from "../api/errors";
import type { ApiClient } from "@/api/client";
import { AsyncState } from "@/stores/AsyncState";

/**
 * Whether a receipt's printed total still needs the user (BRD A11): none was
 * read, or it was read with low confidence. One decision either way, so the
 * "N things" counter and the cards on both wizard steps agree.
 */
export function totalNeedsDecision(extraction: {
  receipt_total?: unknown;
  receipt_total_confidence?: unknown;
}): boolean {
  if (!extraction.receipt_total) return true;
  return (
    typeof extraction.receipt_total_confidence === "number" &&
    extraction.receipt_total_confidence < 80
  );
}

export class UploadStore {
  readonly uploadState = new AsyncState();
  errorDetails: string | null = null;
  fileIds: string[] = [];
  jobId: string | null = null;
  isProcessing = false;
  errorTitle: string | null = null;
  api: ApiClient;
  extractedData: Record<string, unknown> | null = null;
  totalItems = 0;
  processedItems = 0;
  selectedIndices = new Set<number>();
  editingExtractionIndex: number | null = null;

  mode: "single" | "multiple" = "single";
  lines: File[][] = [[]];
  currentStep: 1 | 2 | 3 = 1;

  isCommitting = false;
  private readonly toastStore: ToastStore | undefined;

  constructor(api: ApiClient, toastStore?: ToastStore) {
    this.api = api;
    this.toastStore = toastStore;
    makeAutoObservable(this);
  }

  /**
   * Tell the user a wizard action failed, and report whether it succeeded.
   *
   * Every action here is fired from a click handler that cannot await it, so
   * an error thrown back to the caller vanished unseen; it is shown here instead.
   */
  private report(error: unknown, fallback: string): false {
    console.error(error);
    this.toastStore?.showError(error instanceof Error ? error.message : fallback);
    return false;
  }

  startEditingExtraction(index: number) {
    this.editingExtractionIndex = index;
  }

  stopEditingExtraction() {
    this.editingExtractionIndex = null;
  }

  toggleSelection(index: number) {
    if (this.selectedIndices.has(index)) {
      this.selectedIndices.delete(index);
    } else {
      this.selectedIndices.add(index);
    }
  }

  setMode(mode: "single" | "multiple") {
    this.mode = mode;
    // reset lines if needed
    if (mode === "single") {
      this.lines = [this.lines[0] ?? []];
    } else {
      if (this.lines.length === 0) {
        this.lines = [[]];
      }
    }
  }

  get files() {
    return this.lines[0] ?? [];
  }

  // legacy method for single mode
  addFiles(newFiles: File[]) {
    this.addFilesToLine(0, newFiles);
  }

  // legacy method for single mode
  removeFile(index: number) {
    this.removeFileFromLine(0, index);
  }

  addFilesToLine(lineIndex: number, newFiles: File[]) {
    this.lines[lineIndex] ??= [];
    this.lines[lineIndex] = [...this.lines[lineIndex], ...newFiles];
  }

  removeFileFromLine(lineIndex: number, fileIndex: number) {
    if (this.lines[lineIndex]) {
      this.lines[lineIndex].splice(fileIndex, 1);
    }
  }

  addLine() {
    this.lines.push([]);
  }

  removeLine(lineIndex: number) {
    this.lines.splice(lineIndex, 1);
  }

  get totalSize() {
    return this.files.reduce((acc, file) => acc + file.size, 0);
  }

  get totalSizeMB() {
    return (this.totalSize / (1024 * 1024)).toFixed(1);
  }

  get isOverLimit() {
    return this.files.length > 10 || this.totalSize > 50 * 1024 * 1024;
  }

  getLineTotalSize(lineIndex: number) {
    const line = this.lines[lineIndex] ?? [];
    return line.reduce((acc, file) => acc + file.size, 0);
  }

  getLineTotalSizeMB(lineIndex: number) {
    return (this.getLineTotalSize(lineIndex) / (1024 * 1024)).toFixed(1);
  }

  isLineOverLimit(lineIndex: number) {
    const line = this.lines[lineIndex] ?? [];
    return line.length > 10 || this.getLineTotalSize(lineIndex) > 50 * 1024 * 1024;
  }

  get isAnyLineOverLimit() {
    return this.lines.some((_, i) => this.isLineOverLimit(i));
  }

  get totalFilesCount() {
    return this.lines.reduce((acc, line) => acc + line.length, 0);
  }

  get allLinesTotalSizeMB() {
    const size = this.lines.reduce((acc, _, i) => acc + this.getLineTotalSize(i), 0);
    return (size / (1024 * 1024)).toFixed(1);
  }

  async submitUpload(): Promise<boolean> {
    if (this.totalFilesCount === 0) return false;

    this.uploadState.start();
    this.errorDetails = null;
    this.errorTitle = null;
    this.jobId = null;
    this.isProcessing = false;
    this.extractedData = null;
    this.totalItems = 0;
    this.processedItems = 0;
    this.selectedIndices.clear();

    try {
      const formData = new FormData();

      let error: unknown;
      let response: { status: number } = { status: 200 };
      let data: { job_id?: string } | undefined;

      if (this.mode === "single") {
        for (const file of this.files) {
          formData.append("files", file);
        }
        const res = await this.api.POST("/receipts/upload", {
          // @ts-expect-error openapi-fetch types do not correctly handle FormData
          body: formData,
        });
        error = res.error;
        response = res.response;
        data = res.data;
      } else {
        this.lines.forEach((line, index) => {
          for (const file of line) {
            formData.append(`line_${String(index)}`, file);
          }
        });
        const res = await this.api.POST("/receipts/upload/batch", {
          // @ts-expect-error openapi-fetch types do not correctly handle FormData
          body: formData,
        });
        error = res.error;
        response = res.response;
        data = res.data;
      }

      const startedJobId = runInAction(() => {
        if (error) {
          type ApiError =
            { detail?: { msg: string }[]; title?: string } | { detail?: string; title?: string };
          const typedError = error as ApiError;

          let errorMsg = "Upload failed";
          if (Array.isArray(typedError.detail) && typedError.detail[0]?.msg) {
            errorMsg = typedError.detail[0].msg;
          } else if (typeof typedError.detail === "string") {
            errorMsg = typedError.detail;
          }

          this.uploadState.fail(errorMsg);

          if ((response.status === 415 || response.status === 400) && typedError.title) {
            this.errorTitle = typedError.title;
            this.errorDetails =
              typeof typedError.detail === "string" ? typedError.detail : "Unknown error";
          } else {
            this.errorTitle = "Upload Error";
            this.errorDetails = "An unexpected error occurred during upload.";
          }
          return null;
        } else {
          if (data?.job_id) {
            this.jobId = data.job_id;
            this.isProcessing = true;
            return data.job_id;
          }
          return null;
        }
      });

      if (startedJobId) {
        void this.pollJobStatus(startedJobId);
      }
      return startedJobId !== null;
    } catch {
      runInAction(() => {
        this.uploadState.fail("Network error");
        this.errorTitle = "Network Error";
        this.errorDetails = "Failed to communicate with the server.";
      });
      return false;
    }
  }

  async pollJobStatus(jobId: string) {
    let polling = true;
    while (polling) {
      try {
        const res = await this.api.GET("/receipts/upload/{job_id}", {
          params: { path: { job_id: jobId } },
        });

        if (res.data) {
          runInAction(() => {
            this.totalItems = res.data.total_items;
            this.processedItems = res.data.processed_items;

            if (res.data.status === "completed") {
              this.isProcessing = false;
              this.uploadState.succeed();
              this.fileIds = res.data.file_ids;
              this.extractedData = res.data.extracted_data ?? null;

              this.selectedIndices.clear();
              if (this.extractedData?.extractions) {
                const extractions = this.extractedData.extractions as Record<string, unknown>[];
                extractions.forEach((ext, idx) => {
                  if (!ext.error) {
                    this.selectedIndices.add(idx);
                  }
                });
              }

              this.currentStep = 2;
              polling = false;
            } else if (res.data.status === "failed") {
              this.isProcessing = false;
              this.uploadState.fail("Background processing failed");
              this.errorTitle = "Processing Error";
              this.errorDetails = "An error occurred while reading the receipt.";
              polling = false;
            }
          });
        } else {
          runInAction(() => {
            this.isProcessing = false;
            this.uploadState.fail("Polling failed");
            this.errorTitle = "Network Error";
            this.errorDetails = "Failed to fetch job status.";
          });
          polling = false;
        }
      } catch (err) {
        console.error("Polling error", err);
      }

      if (polling) {
        await new Promise((resolve) => setTimeout(resolve, 2000));
      }
    }
  }

  resetError() {
    this.errorTitle = null;
    this.errorDetails = null;
    this.uploadState.reset();
  }

  resetData() {
    this.extractedData = null;
    this.fileIds = [];
    this.totalItems = 0;
    this.processedItems = 0;
    this.selectedIndices.clear();
    this.currentStep = 1;
  }

  /**
   * Back to an empty first step, ready for the next receipt.
   *
   * Unlike `resetData`, which "Back to photos" uses to keep the chosen photos for
   * another try, this also forgets the photos, the mode and the job: they belong
   * to receipts that are now stored.
   */
  startOver() {
    this.resetData();
    this.resetError();
    this.lines = [[]];
    this.mode = "single";
    this.jobId = null;
    this.isProcessing = false;
    this.editingExtractionIndex = null;
  }

  /** How many receipts a commit of the current selection would store; skipped duplicates don't count. */
  get receiptsToStore(): number {
    const extractions = (this.extractedData?.extractions ?? []) as Record<string, unknown>[];
    return Array.from(this.selectedIndices).filter((i) => {
      const extraction = extractions[i];
      return extraction && !extraction.is_skipped && extraction.duplicate_resolved !== "skipped";
    }).length;
  }

  // Legacy method for existing tests/components
  async uploadFile(file: File): Promise<boolean> {
    this.addFiles([file]);
    return this.submitUpload();
  }

  /**
   * Submits the user's decision (store or skip) for a flagged duplicate receipt.
   * Resolves the extraction server-side so it can proceed or be discarded.
   */
  async resolveDuplicate(index: number, action: "store" | "skip"): Promise<boolean> {
    if (!this.jobId) return false;
    try {
      const res = await this.api.POST("/receipts/upload/{job_id}/resolve-duplicate", {
        params: { path: { job_id: this.jobId } },
        body: { extraction_index: index, action },
      });
      if (res.error) throw new Error(errorMessage(res.error, "Failed to resolve the duplicate"));
      runInAction(() => {
        this.extractedData = res.data.extracted_data ?? null;
      });
      return true;
    } catch (err) {
      return this.report(err, "Failed to resolve the duplicate");
    }
  }

  /**
   * Overrides an automatic position match decision (BRD B7).
   */
  async resolvePositionMatch(
    extractionIndex: number,
    matchIndex: number,
    action: "same" | "different",
  ): Promise<boolean> {
    if (!this.jobId) return false;
    try {
      const res = await this.api.POST("/receipts/upload/{job_id}/resolve-position-match", {
        params: { path: { job_id: this.jobId } },
        body: { extraction_index: extractionIndex, match_index: matchIndex, action },
      });
      if (res.error) throw new Error(errorMessage(res.error, "Failed to resolve match"));
      runInAction(() => {
        if (res.data.extracted_data) {
          this.extractedData = res.data.extracted_data;
        }
      });
      return true;
    } catch (err) {
      return this.report(err, "Failed to resolve match");
    }
  }
  get conflictsCount(): number {
    if (!this.extractedData) return 0;
    const payload = this.extractedData;
    const extractions = (payload.extractions ?? []) as Record<string, unknown>[];
    let count = 0;
    for (let i = 0; i < extractions.length; i++) {
      if (!this.selectedIndices.has(i)) continue;

      const extraction = extractions[i];
      if (!extraction) continue;

      if (extraction.is_duplicate && !extraction.duplicate_resolved) {
        count++;
      }
      if (totalNeedsDecision(extraction)) {
        count++;
      }
      const positionMatches = (extraction.position_matches ?? []) as Record<string, unknown>[];
      for (const match of positionMatches) {
        if (match.result !== "same" && match.result !== "different") {
          count++;
        }
      }
    }
    return count;
  }

  async resolveTotal(extractionIndex: number, receiptTotal: string): Promise<boolean> {
    if (!this.jobId) return false;
    try {
      const res = await this.api.POST("/receipts/upload/{job_id}/resolve-total", {
        params: { path: { job_id: this.jobId } },
        body: { extraction_index: extractionIndex, receipt_total: receiptTotal },
      });
      if (res.error) throw new Error(errorMessage(res.error, "Failed to resolve total"));
      runInAction(() => {
        if (res.data.extracted_data) {
          this.extractedData = res.data.extracted_data;
        }
      });
      return true;
    } catch (err) {
      return this.report(err, "Failed to resolve total");
    }
  }

  /**
   * Correct one line item the parser misread, before anything is stored.
   *
   * Only the fields given are sent: the backend leaves the rest as parsed, and
   * an empty string clears a price rather than setting it to zero. The response
   * carries the recomputed totals, so the footer and the commit gate update
   * from the same round trip.
   */
  async updateLineItem(
    extractionIndex: number,
    itemIndex: number,
    values: { name?: string; quantity?: string; unit_price?: string; total_price?: string },
  ) {
    if (!this.jobId) return false;
    try {
      const res = await this.api.POST("/receipts/upload/{job_id}/line-item", {
        params: { path: { job_id: this.jobId } },
        body: { extraction_index: extractionIndex, item_index: itemIndex, ...values },
      });
      if (res.error) throw new Error(errorMessage(res.error, "Failed to update the line"));
      runInAction(() => {
        if (res.data.extracted_data) {
          this.extractedData = res.data.extracted_data;
        }
      });
      return true;
    } catch (err) {
      return this.report(err, "Failed to update the line");
    }
  }

  /**
   * Store the selected receipts and start the wizard afresh for the next one (F4.7).
   *
   * Stays on the upload page rather than leaving it: receipts are usually added
   * several in a row. The server re-checks every gate, so a refusal is shown
   * rather than swallowed; the button is disabled meanwhile so one click stores once.
   */
  async commitJob(): Promise<boolean> {
    if (!this.jobId || this.isCommitting) return false;
    this.isCommitting = true;
    const stored = this.receiptsToStore;
    try {
      const res = await this.api.POST("/receipts/upload/{job_id}/commit", {
        params: { path: { job_id: this.jobId } },
        body: { indices_to_store: Array.from(this.selectedIndices) },
      });
      if (res.error) throw new Error(errorMessage(res.error, "Failed to store the receipts"));
      runInAction(() => {
        this.startOver();
      });
      this.toastStore?.showSuccess(
        stored === 1 ? "1 receipt stored" : `${String(stored)} receipts stored`,
      );
      return true;
    } catch (err) {
      return this.report(err, "Failed to store the receipts");
    } finally {
      runInAction(() => {
        this.isCommitting = false;
      });
    }
  }
}
