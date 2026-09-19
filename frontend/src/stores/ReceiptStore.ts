import { makeAutoObservable, runInAction } from "mobx";
import type { components } from "../api/schema";
import { apiClient } from "../api/client";
import type { ToastStore } from "./ToastStore";
import { errorMessage } from "../api/errors";

export type Receipt = components["schemas"]["ReceiptResponse"];
export type ReceiptDetail = components["schemas"]["ReceiptDetailResponse"];
export type UpdateReceiptRequest = components["schemas"]["UpdateReceiptRequest"];


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

  pendingDeleteId: string | null = null;
  isDeleting = false;

  isEditingReceipt = false;
  isSavingReceipt = false;
  editReceiptError: string | null = null;

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
        throw new Error(errorMessage(response.error, "Failed to fetch receipts"));
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
        throw new Error(errorMessage(response.error, "Failed to fetch receipt detail"));
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
    this.isEditingReceipt = false;
    this.editReceiptError = null;
  }

  startEditingReceipt() {
    this.isEditingReceipt = true;
    this.editReceiptError = null;
  }

  cancelEditingReceipt() {
    this.isEditingReceipt = false;
    this.editReceiptError = null;
  }

  /**
   * Save a stored receipt's corrected header and line items.
   *
   * Sends the receipt's whole desired state — not a diff — matching what
   * `UpdateReceiptRequest` expects: an existing line resent with its id is
   * updated, one without an id is created, and any existing id left out is
   * deleted server-side. On success this refreshes both the open detail and
   * the row in the list, since the merchant, date or total shown there may
   * have just changed.
   */
  async updateReceipt(id: string, request: UpdateReceiptRequest) {
    this.isSavingReceipt = true;
    this.editReceiptError = null;
    try {
      const response = await apiClient.PATCH("/receipts/{receipt_id}", {
        params: { path: { receipt_id: id } },
        body: request,
      });

      if (response.error) {
        throw new Error(errorMessage(response.error, "Failed to save the receipt"));
      }

      runInAction(() => {
        this.receiptDetail = response.data;
        this.isEditingReceipt = false;
        this.isSavingReceipt = false;
      });

      this.toastStore.showSuccess("Receipt updated");
      await this.fetchReceipts(this.page, this.size);
      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      runInAction(() => {
        this.editReceiptError = message;
        this.isSavingReceipt = false;
      });
      this.toastStore.showError(message);
      return false;
    }
  }

  confirmDelete(id: string) {
    this.pendingDeleteId = id;
  }

  cancelDelete() {
    this.pendingDeleteId = null;
  }

  /**
   * Permanently delete a receipt, its items and its photos.
   *
   * Reloads the current page afterwards, stepping back one when the last row of
   * a page was the one removed, so the user is not left looking at an empty list.
   */
  async deleteReceipt(id: string) {
    this.isDeleting = true;
    try {
      const response = await apiClient.DELETE("/receipts/{receipt_id}", {
        params: { path: { receipt_id: id } },
      });

      if (response.error) {
        throw new Error(errorMessage(response.error, "Failed to delete receipt"));
      }

      const wasLastOnPage = this.receipts.length === 1 && this.page > 1;

      runInAction(() => {
        this.pendingDeleteId = null;
        this.isDeleting = false;
        if (this.selectedReceiptId === id) this.clearSelection();
      });

      this.toastStore.showSuccess("Receipt deleted");
      await this.fetchReceipts(wasLastOnPage ? this.page - 1 : this.page, this.size);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      runInAction(() => {
        this.isDeleting = false;
      });
      this.toastStore.showError(message);
    }
  }
}
