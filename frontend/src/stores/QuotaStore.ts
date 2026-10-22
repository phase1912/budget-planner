import { makeAutoObservable, runInAction } from "mobx";

import type { components } from "@/api/schema";
import { apiClient } from "@/api/client";
import { settle } from "@/api/errors";

export type ReceiptQuota = components["schemas"]["ReceiptQuotaRead"];

/**
 * What is left of the account's AI credits this month, told as receipts and messages
 * (F21.9; was the receipt quota, F10.6). Shared by the Add screen, which stops offering an
 * upload past it, the assistant and Settings. Unknown stays null: the server enforces the
 * wallet either way, so failing to load it only loses the hint.
 */
export class QuotaStore {
  quota: ReceiptQuota | null = null;

  constructor() {
    makeAutoObservable(this, {}, { autoBind: true });
  }

  /** Whether `receipts` more can be read this month; true while the wallet is unknown. */
  allows(receipts: number): boolean {
    const quota = this.quota;
    if (!quota || quota.unlimited || quota.receipts_left === null) return true;
    return receipts <= quota.receipts_left;
  }

  /** Ask the server for this month's usage. */
  async load(): Promise<void> {
    const response = await settle(() => apiClient.GET("/users/me/quota"));
    runInAction(() => {
      if (!response.error) this.quota = response.data;
    });
  }

  /** Forget everything: a different user is signing in. */
  reset(): void {
    this.quota = null;
  }
}
