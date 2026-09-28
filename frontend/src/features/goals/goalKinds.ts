import type { FinancialKind, Goal, GoalType } from "@/stores/GoalsStore";

/** The one choice the dialog offers: a money goal of one kind, or a lifestyle goal (BRD F1). */
export type GoalChoice = FinancialKind | "lifestyle";

export const GOAL_CHOICES: { value: GoalChoice; label: string; meta: string }[] = [
  {
    value: "spending_ceiling",
    label: "Keep a month's spending under an amount",
    meta: "Spending ceiling",
  },
  { value: "savings_target", label: "Put an amount aside", meta: "Savings target" },
  {
    value: "category_reduction",
    label: "Spend less on one category",
    meta: "Category reduction",
  },
  { value: "lifestyle", label: "Something about how I live", meta: "Lifestyle goal" },
];

/** A goal's choice, from its type and kind. */
export function choiceOf(goal: Pick<Goal, "type" | "financial_kind">): GoalChoice {
  return goal.type === "lifestyle" ? "lifestyle" : (goal.financial_kind ?? "spending_ceiling");
}

/** The type and kind a choice stands for, as the API takes them. */
export function typeOf(choice: GoalChoice): {
  type: GoalType;
  financial_kind: FinancialKind | null;
} {
  return choice === "lifestyle"
    ? { type: "lifestyle", financial_kind: null }
    : { type: "financial", financial_kind: choice };
}

/** "Spending ceiling", "Lifestyle goal": what a card says the goal is. */
export function metaOf(goal: Pick<Goal, "type" | "financial_kind">): string {
  const choice = choiceOf(goal);
  return GOAL_CHOICES.find((c) => c.value === choice)?.meta ?? "Goal";
}
