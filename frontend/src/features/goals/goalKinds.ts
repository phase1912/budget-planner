import i18n from "@/i18n";
import type { FinancialKind, Goal, GoalType } from "@/stores/GoalsStore";

/** The one choice the dialog offers: a money goal of one kind, or a lifestyle goal (BRD F1). */
export type GoalChoice = FinancialKind | "lifestyle";

const KINDS: GoalChoice[] = [
  "spending_ceiling",
  "savings_target",
  "category_reduction",
  "lifestyle",
];

/** The goals the dialog offers, labelled in the current language (F9.9). */
export function goalChoices(): { value: GoalChoice; label: string; meta: string }[] {
  return KINDS.map((value) => ({
    value,
    label: i18n.t(`goals:kinds.${value}.label`),
    meta: i18n.t(`goals:kinds.${value}.meta`),
  }));
}

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
  return i18n.t(`goals:kinds.${choiceOf(goal)}.meta`);
}
