import { describe, expect, it } from "vitest";

import type { GoalProgress } from "@/stores/AdviceStore";
import type { Goal } from "@/stores/GoalsStore";
import { goalMeter } from "./goalMeter";

const goal = (overrides: Partial<Goal>): Goal =>
  ({
    id: "g",
    name: "Goal",
    type: "financial",
    financial_kind: "spending_ceiling",
    target_amount: "3000.00",
    ...overrides,
  }) as Goal;

const pace = (spent: string, onTrack: boolean): GoalProgress =>
  ({ spent, projected: spent, target: "3000.00", on_track: onTrack }) as GoalProgress;

describe("goalMeter", () => {
  it("fills a cap as it is spent, warning when the month heads over", () => {
    expect(goalMeter(goal({}), pace("1500", true), null)).toMatchObject({
      percent: 50,
      tone: "good",
    });
    expect(goalMeter(goal({}), pace("2400", false), null)?.tone).toBe("warn");
    expect(goalMeter(goal({}), pace("3300", false), null)).toMatchObject({
      percent: 100,
      tone: "over",
    });
  });

  it("fills a savings target with what this month leaves free", () => {
    const saving = goal({ financial_kind: "savings_target", target_amount: "1000.00" });
    expect(goalMeter(saving, undefined, 400)).toMatchObject({ percent: 40, tone: "over" });
    expect(goalMeter(saving, undefined, 2500)).toMatchObject({ percent: 100, tone: "good" });
    expect(goalMeter(saving, undefined, -200)?.percent).toBe(0);
  });

  it("draws no ring for a lifestyle goal or one with nothing known yet", () => {
    expect(goalMeter(goal({ type: "lifestyle", target_amount: null }), undefined, 100)).toBeNull();
    expect(goalMeter(goal({}), undefined, null)).toBeNull();
  });
});
