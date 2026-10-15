import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ToastStore } from "./ToastStore";
import { TripsStore } from "./TripsStore";

const api = vi.hoisted(() => ({ GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() }));
vi.mock("@/api/client", () => ({ apiClient: api }));

const SUGGESTION = {
  start: "2026-08-03",
  end: "2026-08-09",
  currency: "EUR",
  receipts: 5,
  amount: "214.30",
};

describe("TripsStore (F20.1)", () => {
  let onChange: ReturnType<typeof vi.fn<() => void>>;
  let store: TripsStore;

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    onChange = vi.fn<() => void>();
    const toast = { showSuccess: vi.fn(), showError: vi.fn() };
    store = new TripsStore(toast as unknown as ToastStore, onChange);
    api.GET.mockImplementation((path: string) =>
      Promise.resolve({ data: path.endsWith("/suggestions") ? [SUGGESTION] : [] }),
    );
  });

  it("keeps a suggestion set aside after the page is opened again", async () => {
    await store.load();
    expect(store.openSuggestions).toHaveLength(1);

    store.dismissSuggestion(SUGGESTION);
    const reopened = new TripsStore({} as ToastStore);
    await reopened.load();

    expect(store.openSuggestions).toEqual([]);
    expect(reopened.openSuggestions).toEqual([]);
  });

  it("moving a receipt fetches the month on screen again", async () => {
    api.PUT.mockResolvedValue({ data: {} });

    await store.placeReceipt("r1", null, true);

    expect(api.PUT).toHaveBeenCalledWith("/api/v1/trips/receipts/{receipt_id}", {
      params: { path: { receipt_id: "r1" } },
      body: { trip_id: null, automatic: true },
    });
    expect(onChange).toHaveBeenCalled();
  });

  it("keeps the server's reason when a trip cannot be saved", async () => {
    api.POST.mockResolvedValue({
      error: { code: "trips_overlap", detail: "Overlaps", params: {} },
    });

    const id = await store.save({
      kind: "personal",
      name: "Egypt",
      start_date: "2026-08-01",
      end_date: "2026-08-08",
    });

    expect(id).toBeNull();
    expect(store.saveError).toBeTruthy();
    expect(onChange).not.toHaveBeenCalled();
  });

  it("changing a receipt's kind reloads the open trip, whose totals follow (F20.2)", async () => {
    api.PUT.mockResolvedValue({ data: {} });
    api.GET.mockResolvedValue({ data: { id: "t1" } });
    await store.loadTrip("t1");

    await store.chooseKind("r1", "transport");

    expect(api.PUT).toHaveBeenCalledWith("/api/v1/trips/receipts/{receipt_id}/kind", {
      params: { path: { receipt_id: "r1" } },
      body: { kind: "transport" },
    });
    expect(api.GET).toHaveBeenLastCalledWith("/api/v1/trips/{trip_id}", {
      params: { path: { trip_id: "t1" } },
    });
  });
});
