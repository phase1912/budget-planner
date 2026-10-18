import { makeAutoObservable, runInAction } from "mobx";

import type { components } from "@/api/schema";
import { apiClient } from "@/api/client";
import { errorMessage, settle } from "@/api/errors";
import type { ToastStore } from "./ToastStore";
import i18n from "@/i18n";

export type Goal = components["schemas"]["GoalRead"];
export type GoalCreate = components["schemas"]["GoalCreate"];
export type GoalUpdate = components["schemas"]["GoalUpdate"];
export type GoalType = Goal["type"];
export type FinancialKind = NonNullable<Goal["financial_kind"]>;
export type GoalCheckRequest = components["schemas"]["GoalCheckRequest"];
export type GoalCheck = components["schemas"]["GoalCheckResponse"];

/**
 * The user's goals and the Goals screen's state (BRD F1 — F8.1).
 *
 * Loading the list and saving a goal are tracked apart, so a save never blanks
 * the cards behind the dialog. A refused save keeps its reason in `saveError`,
 * which the dialog shows beside the form; the server decides what a well formed
 * goal is, so the message is its own.
 */
export class GoalsStore {
  goals: Goal[] = [];
  isLoading = false;
  loadError: string | null = null;
  isSaving = false;
  saveError: string | null = null;
  /** The check of a goal not yet saved (F23.13); null until asked, or when it failed. */
  check: GoalCheck | null = null;
  isChecking = false;

  private readonly toastStore: ToastStore;
  private readonly onGoalsChanged: () => void;

  /**
   * `onGoalsChanged` runs after a goal is added, changed or removed: what depends on
   * a goal's target (its pace this month, F8.7) has to be worked out again.
   */
  constructor(toastStore: ToastStore, onGoalsChanged: () => void = () => undefined) {
    this.toastStore = toastStore;
    this.onGoalsChanged = onGoalsChanged;
    makeAutoObservable<this, "toastStore" | "onGoalsChanged">(
      this,
      { toastStore: false, onGoalsChanged: false },
      { autoBind: true },
    );
  }

  /** Fetch the user's goals, newest first. */
  async load(): Promise<void> {
    this.isLoading = true;
    this.loadError = null;
    const response = await settle(() => apiClient.GET("/api/v1/goals"));
    runInAction(() => {
      this.isLoading = false;
      if (response.error) {
        this.loadError = errorMessage(response.error, i18n.t("messages:goals.loadFailed"));
        return;
      }
      this.goals = response.data;
    });
  }

  /**
   * Ask whether a money goal is within reach before saving it (F23.13). A failed check
   * leaves `check` null; the goal can still be saved, the check is advice, not a gate.
   */
  async checkPlan(request: GoalCheckRequest): Promise<void> {
    this.isChecking = true;
    this.check = null;
    const response = await settle(() => apiClient.POST("/api/v1/goals/check", { body: request }));
    runInAction(() => {
      this.isChecking = false;
      this.check = response.error === undefined ? response.data : null;
    });
  }

  clearCheck(): void {
    this.check = null;
    this.isChecking = false;
  }

  /** State a new goal; resolves to whether it was saved. */
  async create(goal: GoalCreate): Promise<boolean> {
    return this.save(
      () => apiClient.POST("/api/v1/goals", { body: goal }),
      (saved) => {
        this.goals.unshift(saved);
      },
      i18n.t("messages:goals.added"),
    );
  }

  /** Change a goal; only the fields given change. Resolves to whether it was saved. */
  async update(id: string, changes: GoalUpdate): Promise<boolean> {
    return this.save(
      () =>
        apiClient.PATCH("/api/v1/goals/{goal_id}", {
          params: { path: { goal_id: id } },
          body: changes,
        }),
      (saved) => {
        this.goals = this.goals.map((g) => (g.id === id ? saved : g));
      },
      i18n.t("messages:goals.updated"),
    );
  }

  /** Drop a goal. Resolves to whether it was removed. */
  async remove(id: string): Promise<boolean> {
    this.isSaving = true;
    this.saveError = null;
    const response = await settle(() =>
      apiClient.DELETE("/api/v1/goals/{goal_id}", { params: { path: { goal_id: id } } }),
    );
    return runInAction(() => {
      this.isSaving = false;
      if (response.error) {
        this.saveError = errorMessage(response.error, i18n.t("messages:goals.removeFailed"));
        return false;
      }
      this.goals = this.goals.filter((g) => g.id !== id);
      this.toastStore.showSuccess(i18n.t("messages:goals.removed"));
      this.onGoalsChanged();
      return true;
    });
  }

  /** Clear a refused save's reason, e.g. when the dialog closes. */
  clearSaveError(): void {
    this.saveError = null;
  }

  /** Forget everything: a different user is signing in. */
  reset(): void {
    this.goals = [];
    this.isLoading = false;
    this.loadError = null;
    this.isSaving = false;
    this.saveError = null;
  }

  private async save(
    send: () => Promise<{ data?: Goal; error?: unknown }>,
    apply: (saved: Goal) => void,
    done: string,
  ): Promise<boolean> {
    this.isSaving = true;
    this.saveError = null;
    const response = await settle(send);
    return runInAction(() => {
      this.isSaving = false;
      if (response.error || !response.data) {
        this.saveError = errorMessage(response.error, i18n.t("messages:goals.saveFailed"));
        return false;
      }
      apply(response.data);
      this.toastStore.showSuccess(done);
      this.onGoalsChanged();
      return true;
    });
  }
}
