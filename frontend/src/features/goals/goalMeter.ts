import type { GoalProgress } from "@/stores/AdviceStore";
import type { Goal } from "@/stores/GoalsStore";

/** What a goal's ring shows in Plan (plan.html): how full, in which tone, and why. */
export interface GoalMeter {
  percent: number;
  tone: "good" | "warn" | "over";
  line:
    | { kind: "paced"; spent: number; target: number; onTrack: boolean; projected: number }
    | { kind: "saving"; available: number; target: number };
}

/**
 * A money goal's ring (F8.7, F23.13). A cap — on the month or on one category — fills as
 * it is spent, in the server's pace (`progress`). A savings target fills with what this
 * month leaves free to put aside: income after taxes, less bills and spending. A
 * lifestyle goal, or one with nothing known yet, has no ring: null.
 */
export function goalMeter(
  goal: Goal,
  progress: GoalProgress | undefined,
  freeThisMonth: number | null,
): GoalMeter | null {
  if (goal.type !== "financial" || goal.target_amount == null) return null;
  const target = Number(goal.target_amount);
  if (target <= 0) return null;
  if (goal.financial_kind === "savings_target") {
    if (freeThisMonth === null) return null;
    const available = Math.max(0, freeThisMonth);
    const percent = Math.min(100, (available / target) * 100);
    return {
      percent,
      tone: percent >= 100 ? "good" : percent >= 50 ? "warn" : "over",
      line: { kind: "saving", available, target },
    };
  }
  if (!progress) return null;
  const spent = Number(progress.spent);
  return {
    percent: Math.min(100, (spent / target) * 100),
    tone: spent > target ? "over" : progress.on_track ? "good" : "warn",
    line: {
      kind: "paced",
      spent,
      target,
      onTrack: progress.on_track,
      projected: Number(progress.projected),
    },
  };
}
