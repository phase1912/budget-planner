import { makeAutoObservable, runInAction } from "mobx";

import type { components } from "@/api/schema";
import { apiClient } from "@/api/client";
import { errorMessage, settle } from "@/api/errors";
import i18n from "@/i18n";
import type { ToastStore } from "@/stores/ToastStore";

export type Trip = components["schemas"]["TripResponse"];
export type TripDetail = components["schemas"]["TripDetailResponse"];
export type TripRequest = components["schemas"]["TripRequest"];
export type TripSuggestion = components["schemas"]["TripSuggestionResponse"];
export type ExpenseKind = components["schemas"]["ExpenseKind"];

const DISMISSED_KEY = "budget_trip_suggestions_dismissed";

function readDismissed(): string[] {
  try {
    const raw = localStorage.getItem(DISMISSED_KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((v): v is string => typeof v === "string") : [];
  } catch {
    return [];
  }
}

/**
 * The user's trips (F20.1): the list, one trip's page, the suggestions of trips nobody
 * recorded, and recording, changing and deleting trips. A suggestion set aside stays set
 * aside on this browser. Any change here can change the month on screen, so it is
 * fetched again (`onChange`).
 */
export class TripsStore {
  trips: Trip[] = [];
  current: TripDetail | null = null;
  suggestions: TripSuggestion[] = [];
  dismissed: string[] = readDismissed();
  isLoading = false;
  isSaving = false;
  loadError: string | null = null;
  saveError: string | null = null;
  private readonly toastStore: ToastStore;
  private readonly onChange: () => void;

  constructor(toastStore: ToastStore, onChange: () => void = () => undefined) {
    this.toastStore = toastStore;
    this.onChange = onChange;
    makeAutoObservable<this, "toastStore" | "onChange">(
      this,
      { toastStore: false, onChange: false },
      { autoBind: true },
    );
  }

  /** The suggestions the user has not set aside. */
  get openSuggestions(): TripSuggestion[] {
    return this.suggestions.filter((s) => !this.dismissed.includes(`${s.start}:${s.currency}`));
  }

  async load(): Promise<void> {
    this.isLoading = true;
    this.loadError = null;
    const [trips, suggestions] = await Promise.all([
      settle(() => apiClient.GET("/api/v1/trips")),
      settle(() => apiClient.GET("/api/v1/trips/suggestions")),
    ]);
    runInAction(() => {
      this.isLoading = false;
      if (trips.error) {
        this.loadError = errorMessage(trips.error, i18n.t("messages:trips.loadFailed"));
        return;
      }
      this.trips = trips.data;
      this.suggestions = suggestions.error ? [] : suggestions.data;
    });
  }

  async loadTrip(id: string): Promise<void> {
    this.isLoading = true;
    this.loadError = null;
    const response = await settle(() =>
      apiClient.GET("/api/v1/trips/{trip_id}", { params: { path: { trip_id: id } } }),
    );
    runInAction(() => {
      this.isLoading = false;
      if (response.error) {
        this.current = null;
        this.loadError = errorMessage(response.error, i18n.t("messages:trips.loadFailed"));
        return;
      }
      this.current = response.data;
    });
  }

  /** Record a trip, or change `id`; the trip's id when saved, else null with `saveError`. */
  async save(trip: TripRequest, id?: string): Promise<string | null> {
    this.isSaving = true;
    this.saveError = null;
    const response = await settle(() =>
      id
        ? apiClient.PUT("/api/v1/trips/{trip_id}", {
            params: { path: { trip_id: id } },
            body: trip,
          })
        : apiClient.POST("/api/v1/trips", { body: trip }),
    );
    const saved = response.error ? null : response.data.id;
    runInAction(() => {
      this.isSaving = false;
      if (response.error) {
        this.saveError = errorMessage(response.error, i18n.t("messages:trips.saveFailed"));
        return;
      }
      this.toastStore.showSuccess(i18n.t("messages:trips.saved"));
    });
    if (saved) {
      this.onChange();
      await this.load();
      if (this.current?.id === saved) await this.loadTrip(saved);
    }
    return saved;
  }

  async remove(id: string): Promise<boolean> {
    const response = await settle(() =>
      apiClient.DELETE("/api/v1/trips/{trip_id}", { params: { path: { trip_id: id } } }),
    );
    runInAction(() => {
      if (response.error) {
        this.toastStore.showError(
          errorMessage(response.error, i18n.t("messages:trips.deleteFailed")),
        );
        return;
      }
      this.trips = this.trips.filter((t) => t.id !== id);
      this.onChange();
      if (this.current?.id === id) this.current = null;
      this.toastStore.showSuccess(i18n.t("messages:trips.deleted"));
    });
    return response.error === undefined;
  }

  /** Put a receipt in a trip, take it out of any (null), or give it back to its dates. */
  async placeReceipt(
    receiptId: string,
    tripId: string | null,
    automatic = false,
  ): Promise<boolean> {
    const response = await settle(() =>
      apiClient.PUT("/api/v1/trips/receipts/{receipt_id}", {
        params: { path: { receipt_id: receiptId } },
        body: { trip_id: tripId, automatic },
      }),
    );
    if (response.error) {
      this.toastStore.showError(errorMessage(response.error, i18n.t("messages:trips.moveFailed")));
      return false;
    }
    this.onChange();
    await this.load();
    if (this.current) await this.loadTrip(this.current.id);
    return true;
  }

  /** Say what a trip's receipt paid for (F20.2); the trip's totals by kind follow. */
  async chooseKind(receiptId: string, kind: ExpenseKind): Promise<void> {
    const response = await settle(() =>
      apiClient.PUT("/api/v1/trips/receipts/{receipt_id}/kind", {
        params: { path: { receipt_id: receiptId } },
        body: { kind },
      }),
    );
    if (response.error) {
      this.toastStore.showError(errorMessage(response.error, i18n.t("messages:trips.kindFailed")));
      return;
    }
    if (this.current) await this.loadTrip(this.current.id);
  }

  dismissSuggestion(suggestion: TripSuggestion): void {
    this.dismissed = [...this.dismissed, `${suggestion.start}:${suggestion.currency}`];
    try {
      localStorage.setItem(DISMISSED_KEY, JSON.stringify(this.dismissed));
    } catch {
      // Private mode or blocked storage: it stays set aside until the page reloads.
    }
  }

  clearSaveError(): void {
    this.saveError = null;
  }

  /** Forget everything: a different user is signing in. */
  reset(): void {
    this.trips = [];
    this.current = null;
    this.suggestions = [];
    this.loadError = null;
  }
}
