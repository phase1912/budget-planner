import { makeAutoObservable, runInAction } from "mobx";

import type { components } from "@/api/schema";
import { apiClient } from "@/api/client";
import { errorMessage, settle } from "@/api/errors";

export type Recommendation = components["schemas"]["RecommendationRead"];

/** Why the last ask for advice on a goal produced none. */
export interface AdviceOutcome {
  kind: "nothing_specific" | "failed";
  message: string;
}

/**
 * The advice on each of the user's goals (BRD F3 — F8.4), shown in the goal's card.
 *
 * Every goal's advice loads in one request; asking for advice is per goal,
 * because each ask is a call to the model, and one ask runs at a time. Fresh
 * advice replaces that goal's earlier advice, as it does on the server. An ask
 * that finds nothing specific, or fails, is remembered for its goal until the
 * next ask, so the card can say why it has no new advice.
 */
export class AdviceStore {
  recommendations: Recommendation[] = [];
  isLoading = false;
  loadError: string | null = null;
  /** The goal advice is being worked out for, if any. */
  advisingGoalId: string | null = null;
  /** Why the last ask produced no advice, by goal id. */
  outcomes = new Map<string, AdviceOutcome>();

  constructor() {
    makeAutoObservable(this, {}, { autoBind: true });
  }

  /** One goal's current advice, newest first. */
  forGoal(goalId: string): Recommendation[] {
    return this.recommendations.filter((r) => r.goal_id === goalId);
  }

  /** Fetch every current recommendation on the user's goals, newest first. */
  async load(): Promise<void> {
    this.isLoading = true;
    this.loadError = null;
    const response = await settle(() => apiClient.GET("/api/v1/recommendations"));
    runInAction(() => {
      this.isLoading = false;
      if (response.error) {
        this.loadError = errorMessage(response.error, "Your advice could not be loaded");
        return;
      }
      this.recommendations = response.data;
    });
  }

  /** Ask for fresh advice on one goal, replacing what it had. */
  async advise(goalId: string): Promise<void> {
    this.advisingGoalId = goalId;
    this.outcomes.delete(goalId);
    const response = await settle(() =>
      apiClient.POST("/api/v1/goals/{goal_id}/recommendations", {
        params: { path: { goal_id: goalId } },
      }),
    );
    runInAction(() => {
      this.advisingGoalId = null;
      if (response.error) {
        this.outcomes.set(goalId, {
          kind: "failed",
          message: errorMessage(response.error, "Advice could not be worked out"),
        });
        return;
      }
      this.recommendations = [
        ...response.data,
        ...this.recommendations.filter((r) => r.goal_id !== goalId),
      ];
      if (response.data.length === 0) {
        this.outcomes.set(goalId, {
          kind: "nothing_specific",
          message: "Your receipts show nothing specific to act on for this goal yet.",
        });
      }
    });
  }

  /** Forget everything: a different user is signing in. */
  reset(): void {
    this.recommendations = [];
    this.isLoading = false;
    this.loadError = null;
    this.advisingGoalId = null;
    this.outcomes.clear();
  }
}
