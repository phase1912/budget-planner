import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/api/client";
import { AdviceStore } from "./AdviceStore";
import type { Recommendation } from "./AdviceStore";

vi.mock("@/api/client", () => ({ apiClient: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn() } }));

function advice(id: string, goalId: string): Recommendation {
  return {
    id,
    goal_id: goalId,
    target_kind: "item",
    target_name: "Cookies Choco 300g",
    action: `Advice ${id}`,
    rationale: "On 9 of the 14 receipts from Fresh Market.",
    reduction_percent: 100,
    monthly_saving: "20.47",
    purchases_avoided: "3.0",
    feedback: null,
    created_at: "2026-09-30T10:00:00Z",
  };
}

// The client's response types differ per route; the store reads only data and error.
const ok = (data: unknown) => ({ data, response: new Response() }) as never;
const refused = (status: number, detail: string) =>
  ({ error: { title: "Refused", status, detail }, response: new Response() }) as never;

describe("AdviceStore", () => {
  let store: AdviceStore;

  beforeEach(() => {
    vi.mocked(apiClient.GET).mockReset();
    vi.mocked(apiClient.POST).mockReset();
    store = new AdviceStore();
  });

  it("loads every goal's advice in one request, with whether advice can be had", async () => {
    vi.mocked(apiClient.GET).mockResolvedValue(ok([advice("1", "g1"), advice("2", "g2")]));
    await store.load();
    expect(apiClient.GET).toHaveBeenCalledTimes(3);
    expect(apiClient.GET).toHaveBeenCalledWith("/api/v1/recommendations");
    expect(apiClient.GET).toHaveBeenCalledWith("/api/v1/advice/readiness");
    expect(apiClient.GET).toHaveBeenCalledWith("/api/v1/goals/progress");
    expect(store.forGoal("g2").map((r) => r.id)).toEqual(["2"]);
  });

  it("replaces only the advised goal's advice", async () => {
    store.recommendations = [advice("old", "g1"), advice("kept", "g2")];
    vi.mocked(apiClient.POST).mockResolvedValue(ok([advice("new", "g1")]));
    await store.advise("g1");
    expect(store.forGoal("g1").map((r) => r.id)).toEqual(["new"]);
    expect(store.forGoal("g2").map((r) => r.id)).toEqual(["kept"]);
    expect(store.advisingGoalId).toBeNull();
  });

  it("says when the receipts support nothing specific, rather than staying silent", async () => {
    store.recommendations = [advice("old", "g1")];
    vi.mocked(apiClient.POST).mockResolvedValue(ok([]));
    await store.advise("g1");
    expect(store.forGoal("g1")).toEqual([]);
    expect(store.outcomes.get("g1")?.kind).toBe("nothing_specific");
  });

  it("keeps the earlier advice and the server's reason when advice is unavailable", async () => {
    store.recommendations = [advice("old", "g1")];
    vi.mocked(apiClient.POST).mockResolvedValue(refused(503, "Try again in a moment."));
    await store.advise("g1");
    expect(store.forGoal("g1").map((r) => r.id)).toEqual(["old"]);
    expect(store.outcomes.get("g1")).toEqual({ kind: "failed", message: "Try again in a moment." });
  });

  it("keeps one goal's outcome when another goal is advised, and clears it on the next ask", async () => {
    vi.mocked(apiClient.POST)
      .mockResolvedValueOnce(refused(503, "Try again in a moment."))
      .mockResolvedValueOnce(ok([advice("new", "g2")]))
      .mockResolvedValueOnce(ok([advice("fresh", "g1")]));
    await store.advise("g1");
    await store.advise("g2");
    expect(store.outcomes.get("g1")?.kind).toBe("failed");
    await store.advise("g1");
    expect(store.outcomes.has("g1")).toBe(false);
  });

  it("says the server could not be reached instead of failing silently", async () => {
    vi.mocked(apiClient.GET).mockRejectedValue(new TypeError("Failed to fetch"));
    vi.mocked(apiClient.POST).mockRejectedValue(new TypeError("Failed to fetch"));

    await store.load();
    await store.advise("g1");

    expect(store.loadError).toBe("The server could not be reached. Try again in a moment.");
    expect(store.outcomes.get("g1")?.kind).toBe("failed");
    expect(store.advisingGoalId).toBeNull();
  });

  it("forgets the previous user's advice", () => {
    store.recommendations = [advice("1", "g1")];
    store.outcomes.set("g1", { kind: "failed", message: "x" });
    store.reset();
    expect(store.recommendations).toEqual([]);
    expect(store.outcomes.size).toBe(0);
  });

  it("reads too little history as how far there is to go, not as a failure", async () => {
    const readiness = {
      ready: false,
      receipts: 3,
      required_receipts: 4,
      history_days: 0,
      required_days: 30,
      progress: 0,
    };
    vi.mocked(apiClient.POST).mockResolvedValue({
      error: { code: "insufficient_data", detail: "Advice needs about a month" },
      response: new Response(),
    });
    vi.mocked(apiClient.GET).mockResolvedValue(ok(readiness));

    await store.advise("g1");
    await vi.waitFor(() => {
      expect(store.readiness).toEqual(readiness);
    });

    expect(store.outcomes.has("g1")).toBe(false);
  });

  it("forgets the previous user's readiness too", () => {
    store.readiness = {
      ready: true,
      receipts: 9,
      required_receipts: 4,
      history_days: 40,
      required_days: 30,
      progress: 100,
    };
    store.reset();
    expect(store.readiness).toBeNull();
  });

  it("does not call a goal on track short of advice when it gets none", async () => {
    vi.mocked(apiClient.GET).mockResolvedValue(
      ok([
        {
          goal_id: "g1",
          goal_name: "Stay under",
          at_risk: false,
          warning_dismissed: false,
          spent: "100.00",
          projected: "300.00",
          target: "3000.00",
          margin: "2700.00",
          on_track: true,
          day: 10,
          days_in_month: 31,
        },
      ]),
    );
    await store.loadProgress();
    vi.mocked(apiClient.POST).mockResolvedValue(ok([]));

    await store.advise("g1");

    expect(store.progress.get("g1")?.on_track).toBe(true);
    expect(store.outcomes.has("g1")).toBe(false);
  });

  it("keeps a set-aside warning away and lists only goals at risk", async () => {
    const row = (goalId: string, atRisk: boolean) => ({
      goal_id: goalId,
      goal_name: goalId,
      spent: "900.00",
      projected: "1200.00",
      target: "1000.00",
      margin: "-200.00",
      on_track: false,
      at_risk: atRisk,
      warning_dismissed: false,
      day: 20,
      days_in_month: 31,
    });
    vi.mocked(apiClient.GET).mockResolvedValue(ok([row("g1", true), row("g2", false)]));
    await store.loadProgress();
    expect(store.warnings.map((w) => w.goal_id)).toEqual(["g1"]);

    vi.mocked(apiClient.POST).mockResolvedValue({ response: new Response() });
    await store.dismissWarning("g1");

    expect(store.warnings).toEqual([]);
  });

  it("marks advice at once and puts it back when the server refuses", async () => {
    store.recommendations = [advice("1", "g1")];
    vi.mocked(apiClient.PATCH).mockRejectedValueOnce(new TypeError("Failed to fetch"));

    const marking = store.updateFeedback("1", "not_helpful");
    expect(store.forGoal("g1")[0]?.feedback).toBe("not_helpful");
    await marking;
    expect(store.forGoal("g1")[0]?.feedback).toBeNull();

    vi.mocked(apiClient.PATCH).mockResolvedValueOnce(ok(advice("1", "g1")));
    await store.updateFeedback("1", "not_followed");
    expect(store.forGoal("g1")[0]?.feedback).toBe("not_followed");
  });

  it("counts turned-down advice as no new answer, but keeps it on the card", async () => {
    store.recommendations = [];
    vi.mocked(apiClient.POST).mockResolvedValueOnce(
      ok([{ ...advice("1", "g1"), feedback: "not_followed" as const }]),
    );

    await store.advise("g1");

    expect(store.outcomes.get("g1")?.kind).toBe("nothing_specific");
    expect(store.forGoal("g1").map((r) => r.feedback)).toEqual(["not_followed"]);
  });
});
