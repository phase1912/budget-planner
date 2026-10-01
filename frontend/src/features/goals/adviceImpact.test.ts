import { describe, expect, it } from "vitest";

import type { Recommendation } from "@/stores/AdviceStore";
import { impactOf } from "./adviceImpact";

function advice(saving: string, avoided: string | null): Recommendation {
  return {
    id: "r1",
    goal_id: "g1",
    target_kind: avoided === null ? "category" : "item",
    target_name: "Cookies Choco 300g",
    action: "Stop buying them",
    rationale: "On 9 of the 14 receipts from Fresh Market.",
    reduction_percent: 100,
    monthly_saving: saving,
    purchases_avoided: avoided,
    created_at: "2026-10-01T10:00:00Z",
  };
}

describe("impactOf", () => {
  it.each([
    ["1234.5", "3.0", "EUR", "−1,234.50 EUR a month · 3 fewer purchases"],
    ["20.47", "0.5", "PLN", "−20.47 PLN a month · 0.5 fewer purchases"],
    ["8.00", "1.0", "PLN", "−8.00 PLN a month · 1 fewer purchase"],
    ["50.17", null, "PLN", "−50.17 PLN a month"],
    ["0.00", "0.0", "PLN", "−0.00 PLN a month"],
  ])("states %s saved and %s purchases avoided", (saving, avoided, currency, words) => {
    expect(impactOf(advice(saving, avoided), currency)).toBe(words);
  });
});
