import { makeAutoObservable, runInAction } from "mobx";
import type { ApiClient } from "@/api/client";
import { AsyncState } from "@/stores/AsyncState";

export class UploadStore {
  readonly uploadState = new AsyncState();
  errorDetails: string | null = null;
  fileIds: string[] = [];
  errorTitle: string | null = null;
  api: ApiClient;

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

    try {
      const formData = new FormData();

      let error: unknown;
      let response: { status: number } = { status: 200 };
      let data: { file_ids?: string[] } | undefined;

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

      runInAction(() => {
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
        } else {
          this.uploadState.succeed();
          if (data?.file_ids) {
            this.fileIds = data.file_ids;
          }
        }
      });
      return !error;
    } catch {
      runInAction(() => {
        this.uploadState.fail("Network error");
        this.errorTitle = "Network Error";
        this.errorDetails = "Failed to communicate with the server.";
      });
      return false;
    }
  }

  resetError() {
    this.errorTitle = null;
    this.errorDetails = null;
    this.uploadState.reset();
  }

  // Legacy method for existing tests/components
  async uploadFile(file: File): Promise<boolean> {
    this.addFiles([file]);
    return this.submitUpload();
  }
}
