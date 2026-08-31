import { makeAutoObservable, runInAction } from "mobx";
import type { components } from "../api/schema";
import { apiClient } from "../api/client";
import type { ToastStore } from "./ToastStore";

export type Receipt = components["schemas"]["ReceiptResponse"];
export type ReceiptDetail = components["schemas"]["ReceiptDetailResponse"];

export class ReceiptStore {
  receipts: Receipt[] = [];
  total = 0;
  page = 1;
  size = 20;
  pages = 0;

  isLoadingList = false;
  listError: string | null = null;

  selectedReceiptId: string | null = null;
  receiptDetail: ReceiptDetail | null = null;
  isLoadingDetail = false;
  detailError: string | null = null;

  private toastStore: ToastStore;

  constructor(toastStore: ToastStore) {
    this.toastStore = toastStore;
    makeAutoObservable(this, {}, { autoBind: true });
  }

  async fetchReceipts(page = 1, size = 20) {
    this.isLoadingList = true;
    this.listError = null;
    try {
      const response = await apiClient.GET("/receipts", {
        params: {
          query: { page, size },
        },
      });

      if (response.error) {
        const errObj = response.error as { detail?: { msg?: string }[] };
        const msg = errObj.detail?.[0]?.msg;
        throw new Error(typeof msg === "string" ? msg : "Failed to fetch receipts");
      }

      runInAction(() => {
        this.receipts = response.data.items;
        this.total = response.data.total;
        this.page = response.data.page;
        this.size = response.data.size;
        this.pages = response.data.pages;
        this.isLoadingList = false;
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      runInAction(() => {
        this.listError = errorMessage;
        this.isLoadingList = false;
      });
      this.toastStore.showError(errorMessage);
    }
  }

  async fetchReceiptDetail(id: string) {
    this.selectedReceiptId = id;
    this.isLoadingDetail = true;
    this.detailError = null;
    this.receiptDetail = null;

    try {
      const response = await apiClient.GET("/receipts/{receipt_id}", {
        params: {
          path: { receipt_id: id },
        },
      });

      if (response.error) {
        const errObj = response.error as { detail?: { msg?: string }[] };
        const msg = errObj.detail?.[0]?.msg;
        throw new Error(typeof msg === "string" ? msg : "Failed to fetch receipt detail");
      }

      runInAction(() => {
        this.receiptDetail = response.data;
        this.isLoadingDetail = false;
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      runInAction(() => {
        this.detailError = errorMessage;
        this.isLoadingDetail = false;
      });
      this.toastStore.showError(errorMessage);
    }
  }

  clearSelection() {
    this.selectedReceiptId = null;
    this.receiptDetail = null;
  }
}
