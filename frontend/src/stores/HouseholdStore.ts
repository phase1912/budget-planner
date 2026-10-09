import { makeAutoObservable, runInAction } from "mobx";

import type { components } from "@/api/schema";
import { apiClient } from "@/api/client";
import { errorMessage, settle } from "@/api/errors";
import { AsyncState } from "@/stores/AsyncState";
import type { ToastStore } from "@/stores/ToastStore";

export type Household = components["schemas"]["HouseholdRead"];
export type HouseholdMember = components["schemas"]["HouseholdMemberRead"];
export type HouseholdInvite = components["schemas"]["HouseholdInvite"];

/**
 * The signed-in user's household (E12 — F12.2, ADR-0017): who is in it, and the owner's
 * and members' actions on it. `household` is null both before loading and for a user
 * with none; `loaded` tells the two apart.
 */
export class HouseholdStore {
  household: Household | null = null;
  loaded = false;
  readonly saveState = new AsyncState();
  private readonly toastStore: ToastStore;

  constructor(toastStore: ToastStore) {
    this.toastStore = toastStore;
    makeAutoObservable(this, {}, { autoBind: true });
  }

  /** Whether the user owns their household and may manage it. */
  get isOwner(): boolean {
    return this.household?.my_role === "owner";
  }

  /** Read the household, if the user has one. */
  async load(): Promise<void> {
    const response = await settle(() => apiClient.GET("/api/v1/household"));
    runInAction(() => {
      if (!response.error) this.household = response.data ?? null;
      this.loaded = true;
    });
  }

  /** Start a household the user owns. */
  async create(name: string): Promise<boolean> {
    return this.save(
      () => apiClient.POST("/api/v1/household", { body: { name } }),
      "Could not create the household",
      "Household created.",
    );
  }

  /** Rename the household; the owner only. */
  async rename(name: string): Promise<boolean> {
    return this.save(
      () => apiClient.PATCH("/api/v1/household", { body: { name } }),
      "Could not rename the household",
      "Household renamed.",
    );
  }

  /** The owner takes a member out; their access to shared receipts ends at once. */
  async removeMember(userId: string): Promise<boolean> {
    return this.save(
      () =>
        apiClient.DELETE("/api/v1/household/members/{user_id}", {
          params: { path: { user_id: userId } },
        }),
      "Could not remove the member",
      "Member removed.",
    );
  }

  /** Leave the household; the last one out deletes it. */
  async leave(): Promise<boolean> {
    this.saveState.start();
    const response = await settle(() => apiClient.POST("/api/v1/household/leave"));
    return runInAction(() => {
      if (response.error) return this.failed(response.error, "Could not leave the household");
      this.household = null;
      this.saveState.succeed();
      this.toastStore.showSuccess("You left the household.");
      return true;
    });
  }

  /** Replace the invite link; the old one stops working at once. The owner only. */
  async regenerateInvite(): Promise<boolean> {
    return this.save(
      () => apiClient.POST("/api/v1/household/invite/regenerate"),
      "Could not make a new invite link",
      "New invite link made. The old one no longer works.",
    );
  }

  /** The invite link for this household, or null for anyone but its owner. */
  inviteLink(origin: string): string | null {
    const code = this.household?.invite_code;
    return code ? `${origin}/join/${code}` : null;
  }

  /**
   * Whose household an invite link leads to (F12.3), or the reason it leads nowhere.
   * Shown before joining so nobody joins a stranger's household by mistake.
   */
  async readInvite(code: string): Promise<{ invite?: HouseholdInvite; error?: string }> {
    const response = await settle(() =>
      apiClient.GET("/api/v1/household/invites/{code}", { params: { path: { code } } }),
    );
    if (response.error) {
      return { error: errorMessage(response.error, "This invite link is not valid.") };
    }
    return { invite: response.data };
  }

  /**
   * Join the household an invite link leads to. A refusal is left in `saveState.error`
   * for the join page to show beside the button, not raised as a toast as well.
   */
  async join(code: string): Promise<boolean> {
    return this.save(
      () => apiClient.POST("/api/v1/household/join", { body: { code } }),
      "Could not join the household",
      "Welcome to the household.",
      { toastErrors: false },
    );
  }

  /** Forget everything: a different user is signing in. */
  reset(): void {
    this.household = null;
    this.loaded = false;
  }

  private async save(
    send: () => Promise<{ data?: Household; error?: unknown }>,
    failure: string,
    success: string,
    { toastErrors = true }: { toastErrors?: boolean } = {},
  ): Promise<boolean> {
    this.saveState.start();
    const response = await settle(send);
    return runInAction(() => {
      if (response.error || !response.data)
        return this.failed(response.error, failure, toastErrors);
      this.household = response.data;
      this.saveState.succeed();
      this.toastStore.showSuccess(success);
      return true;
    });
  }

  private failed(error: unknown, fallback: string, toast = true): false {
    const message = errorMessage(error, fallback);
    this.saveState.fail(message);
    if (toast) this.toastStore.showError(message);
    return false;
  }
}
