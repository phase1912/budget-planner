import { makeAutoObservable, runInAction } from "mobx";
import type { ApiClient } from "@/api/client";
import { AsyncState } from "@/stores/AsyncState";

export class UploadStore {
  readonly uploadState = new AsyncState();
  errorDetails: string | null = null;
  errorTitle: string | null = null;
  api: ApiClient;

  constructor(api: ApiClient) {
    this.api = api;
    makeAutoObservable(this);
  }

  async uploadFile(file: File): Promise<boolean> {
    this.uploadState.start();
    this.errorDetails = null;
    this.errorTitle = null;

    try {
      const formData = new FormData();
      formData.append("file", file);

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

          if (response.status === 415 && typedError.title) {
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
}
