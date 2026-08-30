import { makeAutoObservable, runInAction } from "mobx";
import type { ApiClient } from "@/api/client";
import { AsyncState } from "@/stores/AsyncState";

export class UploadStore {
  readonly uploadState = new AsyncState();
  errorDetails: string | null = null;
  fileIds: string[] = [];
  jobId: string | null = null;
  isProcessing = false;
  errorTitle: string | null = null;
  api: ApiClient;
  extractedData: Record<string, unknown> | null = null;

  mode: "single" | "multiple" = "single";
  lines: File[][] = [[]];

  constructor(api: ApiClient) {
    this.api = api;
    makeAutoObservable(this);
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
            if (res.data.status === "completed") {
              this.isProcessing = false;
              this.uploadState.succeed();
              this.fileIds = res.data.file_ids;
              this.extractedData = res.data.extracted_data ?? null;
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
  async resolveDuplicate(index: number, action: "store" | "skip") {
    if (!this.jobId) return;
    try {
      const res = await this.api.POST("/receipts/upload/{job_id}/resolve-duplicate", {
        params: { path: { job_id: this.jobId } },
        body: { extraction_index: index, action },
      });
      if (res.data) {
        runInAction(() => {
          this.extractedData = res.data.extracted_data ?? null;
        });
      }
    } catch (err) {
      console.error("Resolve duplicate error", err);
    }
  }
}
