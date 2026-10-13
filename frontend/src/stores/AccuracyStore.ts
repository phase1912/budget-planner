import { makeAutoObservable, runInAction } from "mobx";

import type { components } from "@/api/schema";
import { apiClient } from "@/api/client";
import { settle } from "@/api/errors";

export type ReadingAccuracy = components["schemas"]["ReadingAccuracyResponse"];

/**
 * How often the user's receipts needed correcting after reading (F15.4), for the panel
 * in Preferences. Unknown stays null: failing to load it only hides the panel.
 */
export class AccuracyStore {
  report: ReadingAccuracy | null = null;

  constructor() {
    makeAutoObservable(this, {}, { autoBind: true });
  }

  /** Ask the server for the last six months' figures. */
  async load(): Promise<void> {
    const response = await settle(() => apiClient.GET("/api/v1/statistics/reading-accuracy"));
    runInAction(() => {
      if (!response.error) this.report = response.data;
    });
  }

  /** Forget everything: a different user is signing in. */
  reset(): void {
    this.report = null;
  }
}
