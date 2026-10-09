import { makeAutoObservable, runInAction } from "mobx";

import type { components } from "@/api/schema";
import { apiClient } from "@/api/client";
import { settle } from "@/api/errors";

export type ReceiptQuota = components["schemas"]["ReceiptQuotaRead"];

/**
 * How many receipts the account may still have read this month (BRD F10 — F10.6).
 * Shared by the upload screen, which stops offering an upload past the limit, and the
 * profile, which shows the month's usage. Unknown stays null: the server enforces the
 * limit either way, so failing to load it only loses the hint.
 */
export class QuotaStore {
  quota: ReceiptQuota | null = null;

  constructor() {
    makeAutoObservable(this, {}, { autoBind: true });
  }

  /** Whether `receipts` more can be read this month; true while the quota is unknown. */
  allows(receipts: number): boolean {
    const quota = this.quota;
    if (!quota || quota.unlimited || quota.remaining === null) return true;
    return receipts <= quota.remaining;
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
