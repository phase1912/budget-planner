import { makeAutoObservable, runInAction } from "mobx";
import type { ApiClient } from "@/api/client";
import { AsyncState } from "@/stores/AsyncState";

export class UploadStore {
  readonly uploadState = new AsyncState();
  errorDetails: string | null = null;
  errorTitle: string | null = null;
  api: ApiClient;

  mode: "single" | "multiple" = "single";
  files: File[] = [];

  constructor(api: ApiClient) {
    this.api = api;
    makeAutoObservable(this);
  }

  setMode(mode: "single" | "multiple") {
    this.mode = mode;
  }

  addFiles(newFiles: File[]) {
    this.files = [...this.files, ...newFiles];
  }

  removeFile(index: number) {
    this.files.splice(index, 1);
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

  async submitUpload(): Promise<boolean> {
    if (this.files.length === 0) return false;

    this.uploadState.start();
    this.errorDetails = null;
    this.errorTitle = null;

    try {
      const formData = new FormData();
      for (const file of this.files) {
        formData.append("files", file);
      }

      const { error, response } = await this.api.POST("/receipts/upload", {
        // @ts-expect-error openapi-fetch types do not correctly handle FormData
        body: formData,
      });

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
