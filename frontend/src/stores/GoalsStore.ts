import { makeAutoObservable, runInAction } from "mobx";

import type { components } from "@/api/schema";
import { apiClient } from "@/api/client";
import { errorMessage, settle } from "@/api/errors";
import type { ToastStore } from "./ToastStore";

export type Goal = components["schemas"]["GoalRead"];
export type GoalCreate = components["schemas"]["GoalCreate"];
export type GoalUpdate = components["schemas"]["GoalUpdate"];
export type GoalType = Goal["type"];
export type FinancialKind = NonNullable<Goal["financial_kind"]>;

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
        this.loadError = errorMessage(response.error, "Your goals could not be loaded");
        return;
      }
      this.goals = response.data;
    });
  }

  /** State a new goal; resolves to whether it was saved. */
  async create(goal: GoalCreate): Promise<boolean> {
    return this.save(
      () => apiClient.POST("/api/v1/goals", { body: goal }),
      (saved) => {
        this.goals.unshift(saved);
      },
      "Goal added",
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
      "Goal updated",
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
        this.saveError = errorMessage(response.error, "The goal could not be removed");
        return false;
      }
      this.goals = this.goals.filter((g) => g.id !== id);
      this.toastStore.showSuccess("Goal removed");
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
        this.saveError = errorMessage(response.error, "The goal could not be saved");
        return false;
      }
      apply(response.data);
      this.toastStore.showSuccess(done);
      this.onGoalsChanged();
      return true;
    });
  }
}
