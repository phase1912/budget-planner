import { makeAutoObservable, runInAction } from "mobx";
import type { components } from "../api/schema";
import { apiClient } from "../api/client";
import type { ToastStore } from "./ToastStore";
import { errorMessage } from "../api/errors";
import { purchaseMonth } from "@/shared/purchaseDate";

export type Receipt = components["schemas"]["ReceiptResponse"];
export type ReceiptDetail = components["schemas"]["ReceiptDetailResponse"];
export type UpdateReceiptRequest = components["schemas"]["UpdateReceiptRequest"];

type Dated = Pick<Receipt, "transaction_date" | "created_at">;

const MONTH_AND_YEAR = new Intl.DateTimeFormat("en-GB", {
  month: "long",
  year: "numeric",
  timeZone: "UTC",
});

/**
 * The toast confirming a change, naming each finished month it recalculated.
 *
 * A finished month's figure is a stored snapshot (D5), so saying it was
 * recalculated is what tells the user a closed month has moved (D6). A month
 * still running recalculates on every look and needs no mention. Each receipt
 * is filed under its printed date, else its upload date, like the month total.
 */
export function changeMessage(done: string, receipts: Dated[], now: Date): string {
  const current = now.getFullYear() * 12 + now.getMonth();
  const closed = new Map<number, string>();
  for (const receipt of receipts) {
    const { year, month } = purchaseMonth(receipt.transaction_date ?? receipt.created_at);
    const index = year * 12 + month - 1;
    if (index < current) {
      closed.set(index, MONTH_AND_YEAR.format(new Date(Date.UTC(year, month - 1, 1))));
    }
  }
  if (closed.size === 0) return done;
  const months = [...closed.entries()].sort(([a], [b]) => a - b).map(([, label]) => label);
  return `${done}. ${months.join(" and ")} recalculated`;
}

export class ReceiptStore {
  receipts: Receipt[] = [];
  total = 0;
  page = 1;
  size = 20;
  pages = 0;

  statusFilter: components["schemas"]["ReceiptStatus"] | undefined = undefined;
  startDateFilter: string | undefined = undefined;
  endDateFilter: string | undefined = undefined;
  searchQuery: string | undefined = undefined;

  isLoadingList = false;
  listError: string | null = null;

  selectedReceiptId: string | null = null;
  receiptDetail: ReceiptDetail | null = null;
  isLoadingDetail = false;
  detailError: string | null = null;
  isRecategorising = false;

  pendingDeleteId: string | null = null;
  isDeleting = false;

  isEditingReceipt = false;
  isSavingReceipt = false;
  editReceiptError: string | null = null;

  private toastStore: ToastStore;
  private readonly onReceiptsChanged: () => void;
  private readonly now: () => Date;

  /**
   * `onReceiptsChanged` runs after a receipt is corrected or deleted, so views
   * built on the receipts, such as the month figure, can fetch again (D6).
   */
  constructor(
    toastStore: ToastStore,
    onReceiptsChanged: () => void = () => undefined,
    now: () => Date = () => new Date(),
  ) {
    this.toastStore = toastStore;
    this.onReceiptsChanged = onReceiptsChanged;
    this.now = now;
    makeAutoObservable<this, "toastStore" | "onReceiptsChanged" | "now">(
      this,
      { toastStore: false, onReceiptsChanged: false, now: false },
      { autoBind: true },
    );
  }

  setFilters(filters: {
    status?: components["schemas"]["ReceiptStatus"] | undefined;
    startDate?: string | undefined;
    endDate?: string | undefined;
    searchQuery?: string | undefined;
  }) {
    let changed = false;
    if (filters.status !== undefined && this.statusFilter !== filters.status) {
      this.statusFilter = filters.status;
      changed = true;
    } else if (filters.status === undefined && "status" in filters) {
      this.statusFilter = undefined;
      changed = true;
    }

    if (filters.startDate !== undefined && this.startDateFilter !== filters.startDate) {
      this.startDateFilter = filters.startDate;
      changed = true;
    } else if (filters.startDate === undefined && "startDate" in filters) {
      this.startDateFilter = undefined;
      changed = true;
    }

    if (filters.endDate !== undefined && this.endDateFilter !== filters.endDate) {
      this.endDateFilter = filters.endDate;
      changed = true;
    } else if (filters.endDate === undefined && "endDate" in filters) {
      this.endDateFilter = undefined;
      changed = true;
    }

    if (filters.searchQuery !== undefined && this.searchQuery !== filters.searchQuery) {
      this.searchQuery = filters.searchQuery;
      changed = true;
    } else if (filters.searchQuery === undefined && "searchQuery" in filters) {
      this.searchQuery = undefined;
      changed = true;
    }

    if (changed) {
      this.page = 1;
      void this.fetchReceipts(1, this.size);
    }
  }

  async fetchReceipts(page = 1, size = 20) {
    this.isLoadingList = true;
    this.listError = null;
    try {
      const response = await apiClient.GET("/receipts", {
        params: {
          query: {
            page,
            size,
            ...(this.statusFilter && { status: this.statusFilter }),
            ...(this.startDateFilter && { start_date: this.startDateFilter }),
            ...(this.endDateFilter && { end_date: this.endDateFilter }),
            ...(this.searchQuery && { q: this.searchQuery }),
          },
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

  /**
   * Refetch the open receipt without blanking the dialog.
   *
   * Used after an in-place change such as a category reassignment (BRD C4),
   * where flashing a loading state would lose the user's place.
   */
  async reloadReceiptDetail(): Promise<void> {
    const id = this.selectedReceiptId;
    if (!id) return;
    const response = await apiClient.GET("/receipts/{receipt_id}", {
      params: { path: { receipt_id: id } },
    });
    if (response.error) {
      this.toastStore.showError(errorMessage(response.error, "Failed to refresh the receipt"));
      return;
    }
    runInAction(() => {
      if (this.selectedReceiptId === id) this.receiptDetail = response.data;
    });
  }

  /**
   * Re-run automatic categorisation on the open receipt (BRD C3, C4).
   *
   * Categories the owner chose by hand are left alone by the server.
   */
  async recategoriseReceipt(): Promise<void> {
    const id = this.selectedReceiptId;
    if (!id) return;
    this.isRecategorising = true;
    const response = await apiClient.POST("/receipts/{receipt_id}/categorise", {
      params: { path: { receipt_id: id } },
    });
    runInAction(() => {
      this.isRecategorising = false;
      if (response.error) {
        this.toastStore.showError(errorMessage(response.error, "Could not re-run categorisation"));
        return;
      }
      if (this.selectedReceiptId === id) this.receiptDetail = response.data;
      this.toastStore.showSuccess("Categories updated. Your own choices were kept.");
    });
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

      const before = this.receiptDetail;
      runInAction(() => {
        this.receiptDetail = response.data;
        this.isEditingReceipt = false;
        this.isSavingReceipt = false;
      });

      const touched = before ? [before, response.data] : [response.data];
      this.toastStore.showSuccess(changeMessage("Receipt updated", touched, this.now()));
      this.onReceiptsChanged();
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
      const gone =
        this.receiptDetail?.id === id ? this.receiptDetail : this.receipts.find((r) => r.id === id);

      runInAction(() => {
        this.pendingDeleteId = null;
        this.isDeleting = false;
        if (this.selectedReceiptId === id) this.clearSelection();
      });

      this.toastStore.showSuccess(changeMessage("Receipt deleted", gone ? [gone] : [], this.now()));
      this.onReceiptsChanged();
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
